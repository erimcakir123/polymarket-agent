# Public-ESPN-API — COMPLETE Repository Archive

> **Source:** https://github.com/pseudo-r/Public-ESPN-API
>
> This file contains the COMPLETE contents of every file in the repository.
> Total files: 129
> Generated: 2026-04-03 13:21 UTC

---

## File Index

- `.env.example`
- `.github/FUNDING.yml`
- `.github/ISSUE_TEMPLATE/bug_report.md`
- `.github/ISSUE_TEMPLATE/docs_improvement.md`
- `.github/ISSUE_TEMPLATE/missing_endpoint.md`
- `.github/workflows/ci.yml`
- `.gitignore`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `README.md`
- `docker-compose.yml`
- `docs/README.md`
- `docs/response_schemas.md`
- `docs/sports/_global.md`
- `docs/sports/australian_football.md`
- `docs/sports/baseball.md`
- `docs/sports/basketball.md`
- `docs/sports/college_sports.md`
- `docs/sports/cricket.md`
- `docs/sports/field_hockey.md`
- `docs/sports/football.md`
- `docs/sports/golf.md`
- `docs/sports/hockey.md`
- `docs/sports/lacrosse.md`
- `docs/sports/mma.md`
- `docs/sports/racing.md`
- `docs/sports/rugby.md`
- `docs/sports/rugby_league.md`
- `docs/sports/soccer.md`
- `docs/sports/tennis.md`
- `docs/sports/volleyball.md`
- `docs/sports/water_polo.md`
- `espn_service/.env.example`
- `espn_service/.gitignore`
- `espn_service/.pre-commit-config.yaml`
- `espn_service/Dockerfile`
- `espn_service/Makefile`
- `espn_service/README.md`
- `espn_service/apps/__init__.py`
- `espn_service/apps/core/__init__.py`
- `espn_service/apps/core/apps.py`
- `espn_service/apps/core/exceptions.py`
- `espn_service/apps/core/middleware.py`
- `espn_service/apps/core/views.py`
- `espn_service/apps/espn/__init__.py`
- `espn_service/apps/espn/admin.py`
- `espn_service/apps/espn/apps.py`
- `espn_service/apps/espn/filters.py`
- `espn_service/apps/espn/migrations/0001_initial.py`
- `espn_service/apps/espn/migrations/0002_injury_newsarticle_transaction_athleteseasonstats.py`
- `espn_service/apps/espn/migrations/__init__.py`
- `espn_service/apps/espn/models.py`
- `espn_service/apps/espn/serializers.py`
- `espn_service/apps/espn/urls.py`
- `espn_service/apps/espn/views.py`
- `espn_service/apps/ingest/__init__.py`
- `espn_service/apps/ingest/apps.py`
- `espn_service/apps/ingest/management/__init__.py`
- `espn_service/apps/ingest/management/commands/__init__.py`
- `espn_service/apps/ingest/management/commands/ingest_all_teams.py`
- `espn_service/apps/ingest/management/commands/ingest_injuries.py`
- `espn_service/apps/ingest/management/commands/ingest_news.py`
- `espn_service/apps/ingest/management/commands/ingest_scoreboard.py`
- `espn_service/apps/ingest/management/commands/ingest_teams.py`
- `espn_service/apps/ingest/management/commands/ingest_transactions.py`
- `espn_service/apps/ingest/serializers.py`
- `espn_service/apps/ingest/services.py`
- `espn_service/apps/ingest/tasks.py`
- `espn_service/apps/ingest/urls.py`
- `espn_service/apps/ingest/views.py`
- `espn_service/clients/__init__.py`
- `espn_service/clients/espn_client.py`
- `espn_service/config/__init__.py`
- `espn_service/config/asgi.py`
- `espn_service/config/celery.py`
- `espn_service/config/settings/__init__.py`
- `espn_service/config/settings/base.py`
- `espn_service/config/settings/local.py`
- `espn_service/config/settings/production.py`
- `espn_service/config/settings/test.py`
- `espn_service/config/urls.py`
- `espn_service/config/wsgi.py`
- `espn_service/conftest.py`
- `espn_service/docker-compose.prod.yml`
- `espn_service/docker-compose.test.yml`
- `espn_service/docker-compose.yml`
- `espn_service/manage.py`
- `espn_service/pyproject.toml`
- `espn_service/tests/__init__.py`
- `espn_service/tests/conftest.py`
- `espn_service/tests/test_api.py`
- `espn_service/tests/test_espn_client.py`
- `espn_service/tests/test_espn_client_new_methods.py`
- `espn_service/tests/test_ingest_all_teams.py`
- `espn_service/tests/test_ingestion.py`
- `espn_service/tests/test_ingestion_new.py`
- `espn_service/tests/test_models.py`
- `nhl_service/.env.example`
- `nhl_service/.gitignore`
- `nhl_service/Dockerfile`
- `nhl_service/Makefile`
- `nhl_service/apps/__init__.py`
- `nhl_service/apps/ingest/__init__.py`
- `nhl_service/apps/ingest/apps.py`
- `nhl_service/apps/ingest/tasks.py`
- `nhl_service/apps/nhl/admin.py`
- `nhl_service/apps/nhl/apps.py`
- `nhl_service/apps/nhl/migrations/0001_initial.py`
- `nhl_service/apps/nhl/migrations/__init__.py`
- `nhl_service/apps/nhl/models.py`
- `nhl_service/apps/nhl/serializers.py`
- `nhl_service/apps/nhl/views.py`
- `nhl_service/clients/nhl_client.py`
- `nhl_service/config/__init__.py`
- `nhl_service/config/asgi.py`
- `nhl_service/config/celery.py`
- `nhl_service/config/settings/__init__.py`
- `nhl_service/config/settings/base.py`
- `nhl_service/config/settings/local.py`
- `nhl_service/config/settings/production.py`
- `nhl_service/config/settings/test.py`
- `nhl_service/config/urls.py`
- `nhl_service/config/wsgi.py`
- `nhl_service/docker-compose.yml`
- `nhl_service/manage.py`
- `nhl_service/pyproject.toml`
- `nhl_service/tests/__init__.py`
- `nhl_service/tests/conftest.py`
- `nhl_service/tests/test_models.py`

---

---

# FILE: `.env.example`

```
# ─── ESPN Service environment variables ─────────────────────────────────────
# Copy this file to espn_service/.env and fill in your values.
#
#   cp .env.example espn_service/.env

# Django
SECRET_KEY=change-me-to-a-long-random-string
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (PostgreSQL)
# Local: postgres://user:password@host:port/dbname
DATABASE_URL=postgres://postgres:postgres@localhost:5432/espn_db

# Celery / Redis (background task queue)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# ESPN API client settings (optional — defaults shown)
ESPN_TIMEOUT=30
ESPN_MAX_RETRIES=3
ESPN_USER_AGENT=ESPN-Service/1.0

# ESPN API domain URLs (optional — override only if needed)
# Site API  →  scoreboard, teams, news, injuries, standings
ESPN_SITE_API_BASE_URL=https://site.api.espn.com
# Core API  →  events, odds, athletes, play-by-play
ESPN_CORE_API_BASE_URL=https://sports.core.api.espn.com
# Web v3    →  athlete stats, gamelog, splits, overview
ESPN_WEB_V3_API_BASE_URL=https://site.web.api.espn.com
# CDN       →  full game packages (drives, plays, win probability)
ESPN_CDN_API_BASE_URL=https://cdn.espn.com
# Now       →  real-time news feed
ESPN_NOW_API_BASE_URL=https://now.core.api.espn.com


```

---

# FILE: `.github/FUNDING.yml`

```yaml
github: pseudo-r

```

---

# FILE: `.github/ISSUE_TEMPLATE/bug_report.md`

---
name: "🐛 Bug Report"
about: "Report a broken or incorrect API endpoint"
title: "[BUG] "
labels: ["bug"]
assignees: []
---

## Endpoint

<!-- The URL you were trying to use -->
```
GET https://...
```

## Expected Behavior

<!-- What did you expect to get back? -->

## Actual Behavior

<!-- What did you actually get? Include status code and response snippet -->

**Status code:** 
**Response:**
```json

```

## Steps to Reproduce

```bash
curl "https://..."
```

## Environment

- Date tested: 
- Sport/League: 
- Any query params used:

---

# FILE: `.github/ISSUE_TEMPLATE/docs_improvement.md`

---
name: "📝 Documentation Improvement"
about: "Suggest a correction or improvement to the docs"
title: "[DOCS] "
labels: ["documentation"]
assignees: []
---

## File

<!-- Which file needs improving? -->
- [ ] `README.md`
- [ ] `docs/sports/_global.md`
- [ ] `docs/sports/football.md`
- [ ] `docs/sports/basketball.md`
- [ ] `docs/sports/soccer.md`
- [ ] `docs/sports/baseball.md`
- [ ] `docs/sports/hockey.md`
- [ ] `docs/response_schemas.md`
- [ ] Other: 

## What's Wrong / What Could Be Improved

<!-- Describe the issue or improvement -->

## Suggested Fix

<!-- If you know the correct value, paste it here -->

---

# FILE: `.github/ISSUE_TEMPLATE/missing_endpoint.md`

---
name: "🔍 Missing Endpoint"
about: "Report an ESPN API endpoint not yet documented here"
title: "[ENDPOINT] "
labels: ["enhancement", "documentation"]
assignees: []
---

## Endpoint URL

<!-- The full URL of the endpoint you found -->
```
GET https://...
```

## Sport / League

- **Sport slug:** (e.g., `football`, `basketball`)
- **League slug:** (e.g., `nfl`, `nba`)

## Sample Response

<!-- Paste the JSON response (or a relevant excerpt) -->
```json

```

## Description

<!-- What data does this endpoint return? When is it useful? -->

## Source / Reference

<!-- How did you find this endpoint? (Dev tools, another project, etc.) -->

---

# FILE: `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [Public-Api, main]
  pull_request:
    branches: [Public-Api, main]

jobs:
  test:
    name: Test (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest

    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.12", "3.13"]

    defaults:
      run:
        working-directory: espn_service

    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: espn_test
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    env:
      DATABASE_URL: postgres://postgres:postgres@localhost:5432/espn_test
      SECRET_KEY: ci-test-secret-key-not-for-production
      DEBUG: "False"
      CELERY_BROKER_URL: ""

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
          cache-dependency-path: espn_service/pyproject.toml

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Run migrations
        run: python manage.py migrate --settings=config.settings.test

      - name: Run tests (no coverage threshold in CI)
        run: python -m pytest tests/ --no-cov -q

      - name: Run tests with coverage (report only, no fail-under)
        run: python -m pytest tests/ --cov=apps --cov=clients --cov-report=term-missing --cov-report=xml -p no:cov --override-ini="addopts=" -q
        continue-on-error: true

      - name: Upload coverage to Codecov
        if: matrix.python-version == '3.12'
        uses: codecov/codecov-action@v4
        with:
          file: espn_service/coverage.xml
          flags: unittests
          fail_ci_if_error: false


```

---

# FILE: `.gitignore`

```
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/

# Translations
*.mo
*.pot

# Django stuff
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal
staticfiles/
media/

# Flask stuff
instance/
.webassets-cache

# Scrapy stuff
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
target/

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# pyenv
.python-version

# pipenv
Pipfile.lock

# PEP 582
__pypackages__/

# Celery stuff
celerybeat-schedule
celerybeat.pid
celerybeat-schedule.db

# SageMath parsed files
*.sage.py

# Environments
.env
.env.local
.env.*.local
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Pyre type checker
.pyre/

# IDE
.idea/
.vscode/
*.swp
*.swo
*~
*.sublime-project
*.sublime-workspace

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Docker
.docker/

# Node (if any frontend)
node_modules/
npm-debug.log
yarn-error.log

# Ruff
.ruff_cache/

# Redis dump
dump.rdb

# Local development
*.local
.localstack/

# Secrets (never commit these)
*.pem
*.key
secrets.json
credentials.json
service-account.json

# Backup files
*.bak
*.backup
*.old

# Temporary files
*.tmp
*.temp
.temp/
tmp/

```

---

# FILE: `CHANGELOG.md`

# Changelog

All notable changes to the Public ESPN API documentation are listed here.

---

## [Unreleased] — March 2026

### 🆕 Added

#### Documentation
- **`cdn.espn.com` section** — CDN API endpoints for real-time, cached scoreboards
- **`now.core.api.espn.com` section** — Real-time news feed endpoints
- **`site.web.api.espn.com` section** — Search API and rich athlete overview endpoints
- **Site API v3 section** — `site.api.espn.com/apis/site/v3` scoreboard and game summary
- **Notable Specialized Endpoints** section in README covering:
  - QBR (Total Quarterback Rating) — season, weekly, NFL + NCAAF
  - Bracketology (NCAA Tournament live projections)
  - Power Index (BPI / SP+ / FPI)
  - Recruiting (college football & basketball)
  - Coaches (season rosters, career records)
- **Site API endpoint tables** added to all 17 sport-specific docs (`football.md`, `basketball.md`, `baseball.md`, `hockey.md`, `soccer.md`, `golf.md`, `racing.md`, `tennis.md`, `mma.md`, `rugby.md`, `rugby_league.md`, `lacrosse.md`, `cricket.md`, `volleyball.md`, `water_polo.md`, `field_hockey.md`, `australian_football.md`)
- **Specialized Endpoints sections** for:
  - `football.md` — QBR, Recruiting, SP+ Power Index
  - `basketball.md` — Bracketology (with tournament IDs), BPI
- **Core API v2 table expanded** — added `situation`, `broadcasts`, `predictor`, `powerindex`, `competitors/{id}/linescores`, `competitors/{id}/statistics`, `coaches`, `QBR`, seasonal `powerindex`
- **Core API v3 table expanded** — added `athletes/{id}`, `statisticslog`, `plays`
- **Site API v2 table expanded** — added `teams/{id}/depthcharts`, `teams/{id}/injuries`, `teams/{id}/transactions`, `teams/{id}/history`, `athletes/{id}` sub-resources, `calendar` variants
- **Fantasy API improvements** — added `mMatchupScore`, `mScoreboard`, `mStandings`, `mStatus`, `kona_player_info` views and a Segments table (`0`=season, `1–3`=playoff rounds)
- **Betting providers expanded** — FanDuel (37), BetMGM (58), ESPN BET (68) added; `predictor` and `odds-records` endpoints added
- **Parameters Reference expanded** — `lang`, `region`, `xhr`, `calendartype` added
- **CHANGELOG.md** (this file)
- **`docs/response_schemas.md`** — example JSON response structures for common endpoints

#### Code (`espn_service`)
New methods added to `ESPNClient`:
- `get_team_injuries(sport, league, team_id)` — Site API team injury report
- `get_team_depth_chart(sport, league, team_id)` — Site API depth chart
- `get_team_transactions(sport, league, team_id)` — Site API team transactions
- `get_game_situation(sport, league, event_id)` — Core API game situation (down/distance)
- `get_game_predictor(sport, league, event_id)` — ESPN game predictor
- `get_game_broadcasts(sport, league, event_id)` — Broadcast network info
- `get_coaches(sport, league, season)` — Season coaching staff
- `get_coach(sport, league, coach_id)` — Individual coach profile
- `get_qbr(league, season, ...)` — ESPN QBR data (football only)
- `get_power_index(sport, league, season)` — ESPN BPI / SP+ / FPI

### 🔧 Fixed
- **`http://` → `https://`** in `docs/sports/_global.md` — all 350+ Core API v2 endpoints now use secure protocol
- **`http://` → `https://`** in all 17 sport-specific doc files (football, basketball, soccer, etc.)
- **README Table of Contents** — sub-items under "API Endpoint Patterns" now render as proper nested list (fixed 2-space → 4-space indent)

---

## [2.0.0] — February 2026

### 🆕 Added
- Full Django-based `espn_service` with REST API, management commands, and admin
- `ESPNClient` with retry logic, timeouts, structured logging
- `TeamIngestionService` and `ScoreboardIngestionService`
- 17-sport, 139-league WADL mapping in `SPORT_NAMES` and `LEAGUE_INFO`
- `docs/sports/` — individual doc files for all 17 sports

### 🔧 Fixed
- Consolidated all v2/v3 endpoint patterns from ESPN WADL

---

## [1.0.0] — Initial Release

### 🆕 Added
- Initial ESPN API documentation
- README with base URLs, quick start, common endpoints
- `docs/sports/_global.md` with full WADL-sourced endpoint list

---

# FILE: `CONTRIBUTING.md`

# Contributing to Public-ESPN-API

Thank you for your interest in contributing! This project documents the unofficial ESPN API and provides a Django-based service for consuming it.

## Ways to Contribute

### 📖 Documentation
- Add or correct endpoint URLs
- Add missing league slugs for a sport
- Improve or add curl examples
- Add response schema examples to `docs/response_schemas.md`
- Fix errors, typos, or outdated information

### 🐛 Report a Bug
Open an issue using the **🐛 Bug Report** template. Please include:
- The endpoint URL you used
- What you expected
- What you actually received (status code, response snippet)

### 🆕 Report a Missing Endpoint
Open an issue using the **🔍 Missing Endpoint** template. If you've found an ESPN API endpoint not documented here, we want to know!

### 💻 Code (espn_service)
Fix bugs or add features to the Django service. Please include tests for any code changes.

---

## Development Setup

### 🐳 Docker (recommended — one command)

```bash
git clone https://github.com/pseudo-r/Public-ESPN-API.git
cd Public-ESPN-API

# Copy env file
cp .env.example espn_service/.env

# Start PostgreSQL, Redis, Django + Celery
docker compose up
```

API at **http://localhost:8000** · Swagger UI at **http://localhost:8000/api/schema/swagger-ui/**

---

### 🐍 Local (without Docker)

Prerequisites: Python 3.12+, PostgreSQL 14+, Redis 6+.

```bash
cd espn_service
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -e ".[dev]"

# Copy and edit env
cp ../.env.example .env
# Set DATABASE_URL and CELERY_BROKER_URL to your local values

python manage.py migrate
python manage.py runserver
```

---

## Pull Request Guidelines

1. **Branch off `Public-Api`** — this is the default documentation branch
2. **One concern per PR** — keep changes focused
3. **Write clear commit messages** — reference the endpoint or file you changed
4. **Add tests** for any `espn_service` code changes
5. **Update docs** if you change endpoints or add new features

### Commit message format

```
type: short description

- Bullet detail if needed
```

Types: `docs`, `feat`, `fix`, `test`, `chore`

---

## Documentation Style Guide

### Endpoint tables

Use the existing table format in sport-specific docs:

```markdown
| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/teams` | `getTeams` | `page`, `limit`, `active` |
```

### Curl examples

- Use `https://` always (never `http://`)
- Add a `# comment` above each example describing what it does
- Use real, working slugs in examples (e.g., `nba` not `{league}`)

### File locations

| What | Where |
|------|-------|
| Sport-specific endpoints | `docs/sports/{sport}.md` |
| Global endpoint patterns | `docs/sports/_global.md` |
| Response JSON examples | `docs/response_schemas.md` |
| Site-wide docs | `README.md` |
| Change history | `CHANGELOG.md` |

---

## Code of Conduct

Be kind and respectful. This is a community resource — everyone is welcome.

---

## License

By contributing, you agree that your contributions will be licensed under the same [MIT License](LICENSE) as this project.

---

# FILE: `README.md`

<!-- GitAds-Verify: 44FZ4IWPYGNOY6XFRMCK946T5LOIFT23 -->

# ESPN Public API Documentation

**Disclaimer:** This is documentation for ESPN's undocumented public API. I am not affiliated with ESPN. Use responsibly and follow ESPN's terms of service.

[![CI](https://github.com/pseudo-r/Public-ESPN-API/actions/workflows/ci.yml/badge.svg?branch=Public-Api)](https://github.com/pseudo-r/Public-ESPN-API/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/pseudo-r/Public-ESPN-API/branch/Public-Api/graph/badge.svg)](https://codecov.io/gh/pseudo-r/Public-ESPN-API)

---

## ☕ Support This Project

If this documentation has saved you time, consider supporting ongoing development and maintenance:

| Platform | Link |
|----------|------|
| ☕ Buy Me a Coffee | [buymeacoffee.com/pseudo_r](https://buymeacoffee.com/pseudo_r) |
| 💖 GitHub Sponsors | [github.com/sponsors/Kloverdevs](https://github.com/sponsors/Kloverdevs) |
| 💳 PayPal Donate | [PayPal (CAD)](https://www.paypal.com/donate/?business=H5VPFZ2EHVNBU&no_recurring=0&currency_code=CAD) |

Every contribution helps keep this project updated as ESPN changes their API.

---

## 📱 Real-World Apps Built With This API

These apps are live examples of what you can build using this documentation and the included Django service:

### 🏀 [Sportly: Basketball Live](https://play.google.com/store/apps/details?id=com.sportly.basketball)
> Real-time NBA, college basketball, and international leagues — scores, standings, player stats, and live game tracking.

[![Get it on Google Play](https://img.shields.io/badge/Google_Play-Sportly_Basketball-3DDC84?logo=google-play&logoColor=white)](https://play.google.com/store/apps/details?id=com.sportly.basketball)

### ⚽ [Sportly: Soccer Live](https://play.google.com/store/apps/details?id=com.sportly.soccer)
> Premier League, La Liga, Bundesliga, Serie A, MLS, and more — live scores, tables, fixtures, and news.

[![Get it on Google Play](https://img.shields.io/badge/Google_Play-Sportly_Soccer-3DDC84?logo=google-play&logoColor=white)](https://play.google.com/store/apps/details?id=com.sportly.soccer)

### 🏒 [Sportly: NHL & Hockey Live](https://play.google.com/store/apps/details?id=com.sportly.hockey)
> Live NHL scores, standings, game stats, and hockey data across leagues.

[![Get it on Google Play](https://img.shields.io/badge/Google_Play-Sportly_Hockey-3DDC84?logo=google-play&logoColor=white)](https://play.google.com/store/apps/details?id=com.sportly.hockey)

### 🏈 [Sportly: American Football Live](https://play.google.com/store/apps/details?id=com.sportly.football)
> NFL scores, standings, play-by-play, and college football coverage.

[![Get it on Google Play](https://img.shields.io/badge/Google_Play-Sportly_Football-3DDC84?logo=google-play&logoColor=white)](https://play.google.com/store/apps/details?id=com.sportly.football)

### ⚾ [Sportly: Baseball Live](https://play.google.com/store/apps/details?id=com.sportly.baseball)
> MLB scores, box scores, standings, and baseball stats.

[![Get it on Google Play](https://img.shields.io/badge/Google_Play-Sportly_Baseball-3DDC84?logo=google-play&logoColor=white)](https://play.google.com/store/apps/details?id=com.sportly.baseball)



## Table of Contents

- [Overview](#overview)
- [Base URLs](#base-urls)
- [Quick Start](#quick-start)
- [Sports Coverage](#sports-coverage)
- [API Endpoint Patterns](#api-endpoint-patterns)
    - [Site API v2](#site-api-v2-scores-teams-standings)
    - [Site API v3](#site-api-v3-richer-game-data)
    - [Core API v2](#core-api-v2-athletes-stats-events-odds)
    - [Core API v3](#core-api-v3-enriched-schema)
    - [Search & Web API](#search--web-api)
    - [CDN API](#cdn-api-real-time-optimized)
    - [Now API](#now-api-real-time-news)
- [Fantasy Sports API](#fantasy-sports-api)
- [Betting & Odds](#betting--odds)
- [Notable Specialized Endpoints](#notable-specialized-endpoints)
- [Parameters Reference](#parameters-reference)
- [ESPN Service (Django Implementation)](#espn-service-django-implementation)
- [Response Schemas](docs/response_schemas.md)
- [CHANGELOG](CHANGELOG.md)

---

## Overview

ESPN provides undocumented APIs that power their website and mobile apps. These endpoints return JSON data for scores, teams, players, statistics, and more across all major sports.

**Coverage:** 17 sports · 139 leagues · 370 v2 endpoints · 79 v3 endpoints  
*(Mapped from the ESPN WADL at `sports.core.api.espn.com/v2/application.wadl` and `sports.core.api.espn.com/v3/application.wadl`)*

**Additional domains documented:** `site.api.espn.com` (v2 + v3) · `site.web.api.espn.com` · `cdn.espn.com` · `now.core.api.espn.com` · `fantasy.espn.com`

### Important Notes

- **Unofficial:** These APIs are not officially supported and may change without notice
- **No Authentication Required:** Most endpoints are publicly accessible
- **Rate Limiting:** Be respectful — no official limits published, but excessive requests may be blocked
- **Best Practice:** Implement caching and error handling in your applications

---

## Base URLs

| Domain | Version | Purpose |
|--------|---------|---------|
| `site.api.espn.com` | v2/v3 | Scores, news, teams, standings (site-facing) |
| `sports.core.api.espn.com` | v2 | Athletes, stats, odds, play-by-play, detailed data |
| `sports.core.api.espn.com` | v3 | Athletes, leaders (richer schema) |
| `site.web.api.espn.com` | v3 | Search, athlete profiles |
| `cdn.espn.com` | — | CDN-optimized live data |
| `fantasy.espn.com` | v3 | Fantasy sports leagues |
| `now.core.api.espn.com` | — | Real-time news feeds |

---

## Quick Start

```bash
# NFL Scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

# NBA Teams
curl "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams"

# MLB Scores for a Specific Date
curl "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates=20241215"

# NHL Standings — NOTE: use /apis/v2/ (not /apis/site/v2/ which returns a stub)
curl "https://site.api.espn.com/apis/v2/sports/hockey/nhl/standings"
```

---

## Sports Coverage

Each sport has its own detailed endpoint reference document:

| Sport | Slug | # Leagues | Documentation |
|-------|------|-----------|---------------|
| 🏉 Australian Football | `australian-football` | 1 | [docs/sports/australian_football.md](docs/sports/australian_football.md) |
| ⚾ Baseball | `baseball` | 13 | [docs/sports/baseball.md](docs/sports/baseball.md) |
| 🏀 Basketball | `basketball` | 15 | [docs/sports/basketball.md](docs/sports/basketball.md) |
| 🏏 Cricket | `cricket` | varies | [docs/sports/cricket.md](docs/sports/cricket.md) |
| 🏑 Field Hockey | `field-hockey` | 1 | [docs/sports/field_hockey.md](docs/sports/field_hockey.md) |
| 🏈 Football | `football` | 5 | [docs/sports/football.md](docs/sports/football.md) |
| ⛳ Golf | `golf` | 9 | [docs/sports/golf.md](docs/sports/golf.md) |
| 🏒 Hockey | `hockey` | 6 | [docs/sports/hockey.md](docs/sports/hockey.md) |
| 🥍 Lacrosse | `lacrosse` | 4 | [docs/sports/lacrosse.md](docs/sports/lacrosse.md) |
| 🥊 MMA | `mma` | 25+ | [docs/sports/mma.md](docs/sports/mma.md) |
| 🏎️ Racing | `racing` | 5 | [docs/sports/racing.md](docs/sports/racing.md) |
| 🏉 Rugby | `rugby` | 24 | [docs/sports/rugby.md](docs/sports/rugby.md) |
| 🏉 Rugby League | `rugby-league` | 1 | [docs/sports/rugby_league.md](docs/sports/rugby_league.md) |
| ⚽ Soccer | `soccer` | 24 | [docs/sports/soccer.md](docs/sports/soccer.md) |
| 🎾 Tennis | `tennis` | 2 | [docs/sports/tennis.md](docs/sports/tennis.md) |
| 🏐 Volleyball | `volleyball` | 2 | [docs/sports/volleyball.md](docs/sports/volleyball.md) |
| 🤽 Water Polo | `water-polo` | 2 | [docs/sports/water_polo.md](docs/sports/water_polo.md) |

> For global and cross-sport endpoints, see [docs/sports/_global.md](docs/sports/_global.md).

---

## API Endpoint Patterns

### Site API v2 (Scores, Teams, Standings)

```
GET https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/{resource}
```

| Resource | Description |
|----------|-------------|
| `scoreboard` | Live & scheduled events with scores |
| `teams` | All teams in the league |
| `teams/{id}` | Single team detail |
| `teams/{id}/roster` | Team roster |
| `teams/{id}/schedule` | Team schedule |
| `teams/{id}/depthcharts` | Depth chart by position |
| `teams/{id}/injuries` | Current injury report |
| `teams/{id}/transactions` | Recent transactions/moves |
| `teams/{id}/history` | Franchise historical record |
| `athletes/{id}` | Individual athlete profile |
| `athletes/{id}/gamelog` | Game-by-game log |
| `athletes/{id}/splits` | Statistical splits |
| `athletes/{id}/news` | Athlete news |
| `athletes/{id}/bio` | Athlete bio |
| `standings` | League standings ⚠️ use `/apis/v2/` — `/apis/site/v2/` returns a stub |
| `injuries` | League-wide injury report |
| `transactions` | Recent signings/trades/waivers |
| `groups` | Conferences/divisions |
| `news` | Latest news articles |
| `rankings` | Rankings (college sports) |
| `calendar` | Season calendar (all weeks/dates) |
| `calendar/offseason` | Offseason date range |
| `calendar/regular-season` | Regular season weeks |
| `calendar/postseason` | Postseason date ranges |
| `summary?event={id}` | Full game summary |

### Site API v3 (Richer Game Data)

```
GET https://site.api.espn.com/apis/site/v3/sports/{sport}/{league}/{resource}
```

| Resource | Description |
|----------|-------------|
| `scoreboard` | Scoreboard with enriched v3 schema |
| `summary?event={id}` | Enriched game summary (v3 schema) |

### Core API v2 (Athletes, Stats, Events, Odds)

```
GET https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/{resource}
```

| Resource | Description |
|----------|-------------|
| `athletes` | Full athlete list with pagination |
| `athletes/{id}` | Single athlete |
| `athletes/{id}/statistics` | Career stats |
| `athletes/{id}/statisticslog` | Game-by-game log |
| `athletes/{id}/eventlog` | Event history |
| `athletes/{id}/contracts` | Contract info |
| `athletes/{id}/awards` | Awards |
| `athletes/{id}/seasons` | Seasons played |
| `athletes/{id}/records` | Career records |
| `athletes/{id}/hotzones` | Hot zones (baseball) |
| `athletes/{id}/injuries` | Athlete injury history |
| `athletes/{id}/vsathlete/{opponentId}` | Head-to-head stats |
| `events` | Events with full detail |
| `events/{id}/competitions/{id}/odds` | Betting odds |
| `events/{id}/competitions/{id}/probabilities` | Win probabilities |
| `events/{id}/competitions/{id}/plays` | Play-by-play |
| `events/{id}/competitions/{id}/situation` | Current game situation (down/distance/ball) |
| `events/{id}/competitions/{id}/broadcasts` | Broadcast network info |
| `events/{id}/competitions/{id}/predictor` | ESPN game predictor |
| `events/{id}/competitions/{id}/powerindex` | ESPN Power Index for game |
| `events/{id}/competitions/{id}/competitors/{id}/linescores` | Period-by-period scores |
| `events/{id}/competitions/{id}/competitors/{id}/statistics` | Competitor stats |
| `seasons` | Season list |
| `seasons/{year}/teams` | Teams in a season |
| `seasons/{year}/coaches` | Coaching staff |
| `seasons/{year}/draft` | Draft data |
| `seasons/{year}/futures` | Futures odds |
| `seasons/{year}/powerindex` | Season-level Power Index / BPI |
| `seasons/{year}/types/{type}/groups/{group}/qbr/{split}` | ESPN QBR (football) |
| `standings` | League standings |
| `teams` | Teams (detailed) |
| `venues` | Venues/stadiums |
| `leaders` | Statistical leaders |
| `rankings` | Rankings |
| `franchises` | Franchise history |
| `coaches/{id}` | Individual coach profile |
| `coaches/{id}/record/{type}` | Coaching record by type |

### Core API v3 (Enriched Schema)

```
GET https://sports.core.api.espn.com/v3/sports/{sport}/{league}/{resource}
```

| Resource | Description |
|----------|-------------|
| `athletes` | Athletes (enriched schema) |
| `athletes/{id}` | Single athlete (enriched) |
| `athletes/{id}/statisticslog` | Game log (enriched) |
| `athletes/{id}/plays` | Athlete play history |
| `leaders` | Statistical leaders |

### Search & Web API

```
GET https://site.web.api.espn.com/apis/{path}
```

| Endpoint | Description |
|----------|-------------|
| `/search/v2?query={q}&limit={n}` | Global ESPN search |
| `/search/v2?query={q}&sport={sport}` | Sport-scoped search |
| `/v2/scoreboard/header` | Scoreboard header/nav state |
| `/apis/common/v3/sports/{sport}/{league}/athletes/{id}/overview` | Athlete overview (stats snapshot, news, next game) |
| `/apis/common/v3/sports/{sport}/{league}/athletes/{id}/stats` | Season stats (NFL/NBA/NHL/MLB ✅, Soccer ❌) |
| `/apis/common/v3/sports/{sport}/{league}/athletes/{id}/gamelog` | Game-by-game log (NFL/NBA/MLB ✅) |
| `/apis/common/v3/sports/{sport}/{league}/athletes/{id}/splits` | Home/away/opponent splits |
| `/apis/common/v3/sports/{sport}/{league}/statistics/byathlete` | Stats leaderboard with `category=` + `sort=` |

### CDN API (Real-Time Optimized)

```
GET https://cdn.espn.com/core/{sport}/{resource}?xhr=1
```

| Endpoint | Description |
|----------|-------------|
| `/{sport}/scoreboard?xhr=1` | CDN-optimized live scoreboard |
| `/{sport}/scoreboard?xhr=1&league={league}` | Soccer scoreboard (league slug required, e.g. `eng.1`) |
| `/{sport}/game?xhr=1&gameId={id}` | Full game package — drives, plays, win probability, boxscore, odds |
| `/{sport}/boxscore?xhr=1&gameId={id}` | Boxscore only |
| `/{sport}/playbyplay?xhr=1&gameId={id}` | Play-by-play only |

> **Note:** CDN endpoints return JSON when `xhr=1` is passed. The `gamepackageJSON` key holds the full game data object.

### Now API (Real-Time News)

```
GET https://now.core.api.espn.com/v1/sports/news
```

| Endpoint | Description |
|----------|-------------|
| `/v1/sports/news?limit={n}` | Global real-time news feed |
| `/v1/sports/news?sport={sport}&limit={n}` | Sport-filtered news |
| `/v1/sports/news?leagues={league}&limit={n}` | League-filtered news |
| `/v1/sports/news?team={abbrev}&limit={n}` | Team-filtered news |

---

## Common League Slugs

### 🏈 Football (sport: `football`)

| League | Slug |
|--------|------|
| NFL | `nfl` |
| College Football | `college-football` |
| CFL | `cfl` |
| UFL | `ufl` |
| XFL | `xfl` |

### 🏀 Basketball (sport: `basketball`)

| League | Slug |
|--------|------|
| NBA | `nba` |
| WNBA | `wnba` |
| NBA G League | `nba-development` |
| NCAA Men's | `mens-college-basketball` |
| NCAA Women's | `womens-college-basketball` |
| NBL | `nbl` |
| FIBA World Cup | `fiba` |

### ⚾ Baseball (sport: `baseball`)

| League | Slug |
|--------|------|
| MLB | `mlb` |
| NCAA Baseball | `college-baseball` |
| World Baseball Classic | `world-baseball-classic` |
| Dominican Winter League | `dominican-winter-league` |

### 🏒 Hockey (sport: `hockey`)

| League | Slug |
|--------|------|
| NHL | `nhl` |
| NCAA Men's | `mens-college-hockey` |
| NCAA Women's | `womens-college-hockey` |

### ⚽ Soccer (sport: `soccer`)

| League | Slug |
|--------|------|
| FIFA World Cup | `fifa.world` |
| UEFA Champions League | `uefa.champions` |
| English Premier League | `eng.1` |
| Spanish LALIGA | `esp.1` |
| German Bundesliga | `ger.1` |
| Italian Serie A | `ita.1` |
| French Ligue 1 | `fra.1` |
| MLS | `usa.1` |
| Liga MX | `mex.1` |
| NWSL | `usa.nwsl` |
| UEFA Europa League | `uefa.europa` |
| FIFA Women's World Cup | `fifa.wwc` |

### ⛳ Golf (sport: `golf`)

| Tour | Slug |
|------|------|
| PGA TOUR | `pga` |
| LPGA | `lpga` |
| DP World Tour | `eur` |
| LIV Golf | `liv` |
| PGA TOUR Champions | `champions-tour` |
| Korn Ferry Tour | `ntw` |

### 🏎️ Racing (sport: `racing`)

| Series | Slug |
|--------|------|
| Formula 1 | `f1` |
| IndyCar | `irl` |
| NASCAR Cup | `nascar-premier` |
| NASCAR Xfinity | `nascar-secondary` |
| NASCAR Truck | `nascar-truck` |

### 🎾 Tennis (sport: `tennis`)

| Tour | Slug |
|------|------|
| ATP | `atp` |
| WTA | `wta` |

---

## Fantasy Sports API

Base URL: `https://fantasy.espn.com/apis/v3/games/{sport}/seasons/{year}`

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

# With views
?view=mTeam
?view=mRoster
?view=mMatchup
?view=mMatchupScore
?view=mSettings
?view=mDraftDetail
?view=mScoreboard
?view=mStandings
?view=mStatus
?view=kona_player_info
```

### Segments

| Segment | Description |
|---------|-------------|
| `0` | Entire season |
| `1` | Playoff round 1 |
| `2` | Playoff round 2 |
| `3` | Championship |

### Authentication (Private Leagues)

Private leagues require cookies: `espn_s2` and `SWID`

---

## Betting & Odds

Base: `sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}`

| Endpoint | Description |
|----------|-------------|
| `/events/{id}/competitions/{id}/odds` | Game odds |
| `/events/{id}/competitions/{id}/probabilities` | Win probabilities |
| `/events/{id}/competitions/{id}/predictor` | ESPN game predictor |
| `/seasons/{year}/futures` | Season futures |
| `/seasons/{year}/types/{type}/teams/{id}/ats` | ATS records |
| `/seasons/{year}/types/{type}/teams/{id}/odds-records` | Team odds records |

**Betting Provider IDs:**

| Provider | ID |
|----------|----|
| Caesars | 38 |
| FanDuel | 37 |
| DraftKings | 41 |
| BetMGM | 58 |
| ESPN BET | 68 |
| Bet365 | 2000 |

---

## Parameters Reference

### Common Query Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `dates` | Filter by date | `20241215` or `20241201-20241231` |
| `week` | Week number | `1` through `18` |
| `seasontype` | Season type | `1`=preseason, `2`=regular, `3`=postseason |
| `season` | Year | `2024` |
| `limit` | Results limit | `100`, `1000` |
| `page` | Page number | `1` |
| `groups` | Conference ID | `8` (SEC) |
| `enable` | Inline-expand extra data | `roster`, `stats`, `injuries`, `projection` |
| `active` | Active filter | `true` / `false` |
| `lang` | Language / locale | `en`, `es`, `pt` |
| `region` | Regional content filter | `us`, `gb`, `au` |
| `xhr` | CDN JSON signal | `1` (returns JSON on cdn.espn.com) |
| `calendartype` | Calendar view type | `ondays`, `offdays`, `blacklist` |

### Season Types

| Type | Value |
|------|-------|
| Preseason | 1 |
| Regular Season | 2 |
| Postseason | 3 |
| Off Season | 4 |

### College Football Conference IDs (`groups` param)

| Conference | ID |
|------------|----|
| SEC | 8 |
| Big Ten | 5 |
| ACC | 1 |
| Big 12 | 4 |
| Mountain West | 17 |
| Top 25 | 80 |

---

## ESPN Service (Django Implementation)

This repository includes a production-ready Django REST API that wraps ESPN's endpoints.

### Features

- Full support for **17 sports** and **139 leagues**
- Data ingestion and persistence (teams, events, competitors, athletes, venues)
- Clean REST API with filtering and pagination
- Background jobs (Celery)
- Docker support
- OpenAPI documentation via drf-spectacular

### Quick Start

```bash
cd espn_service
docker compose up --build

# API: http://localhost:8000
# Docs: http://localhost:8000/api/docs/
```

### API Endpoints

#### Discovery & Data

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/healthz` | GET | Health check |
| `/api/v1/sports/` | GET | List sports |
| `/api/v1/leagues/` | GET | List leagues (`?sport=basketball`) |
| `/api/v1/teams/` | GET | List teams (`?sport=`, `?league=`, `?search=`) |
| `/api/v1/teams/{id}/` | GET | Team details |
| `/api/v1/teams/espn/{espn_id}/` | GET | Team by ESPN ID |
| `/api/v1/events/` | GET | List events (`?league=`, `?date=`, `?status=`) |
| `/api/v1/events/{id}/` | GET | Event details |
| `/api/v1/events/espn/{espn_id}/` | GET | Event by ESPN ID |
| `/api/v1/news/` | GET | News articles (`?sport=`, `?league=`, `?date_from=`) |
| `/api/v1/news/{id}/` | GET | Article detail |
| `/api/v1/injuries/` | GET | Injury reports (`?sport=`, `?league=`, `?status=`, `?team=`) |
| `/api/v1/injuries/{id}/` | GET | Injury detail |
| `/api/v1/transactions/` | GET | Transactions (`?sport=`, `?league=`, `?date_from=`) |
| `/api/v1/transactions/{id}/` | GET | Transaction detail |
| `/api/v1/athlete-stats/` | GET | Season stats (`?sport=`, `?league=`, `?season=`, `?athlete_espn_id=`) |
| `/api/v1/athlete-stats/{id}/` | GET | Stats detail |

#### Ingest Triggers

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/ingest/teams/` | POST | Ingest ESPN teams |
| `/api/v1/ingest/scoreboard/` | POST | Ingest ESPN events |
| `/api/v1/ingest/news/` | POST | Ingest news articles (`limit` optional) |
| `/api/v1/ingest/injuries/` | POST | Refresh injury snapshot |
| `/api/v1/ingest/transactions/` | POST | Ingest transactions |

### ESPN Client Methods

The `ESPNClient` in `clients/espn_client.py` provides methods covering all major endpoints:

| Category | Methods |
|----------|---------|
| Scoreboard | `get_scoreboard()` |
| Teams | `get_teams()`, `get_team()`, `get_team_roster()`, `get_core_teams()` |
| Events | `get_event()`, `get_core_events()` |
| Standings | `get_standings()` (/apis/v2/), `get_core_standings()` |
| News | `get_news()`, `get_now_news()` |
| Rankings | `get_rankings()` |
| League info | `get_league_injuries()`, `get_league_transactions()`, `get_groups()` |
| Athletes | `get_athletes()`, `get_athlete()`, `get_athletes_v3()`, `get_athlete_statistics()` |
| Athlete v3 | `get_athlete_overview()`, `get_athlete_stats()`, `get_athlete_gamelog()`, `get_athlete_splits()` |
| Stats | `get_leaders()`, `get_leaders_v3()`, `get_statistics_by_athlete()` |
| Seasons | `get_seasons()` |
| Betting | `get_odds()`, `get_win_probabilities()` |
| Play data | `get_plays()`, `get_game_situation()`, `get_game_predictor()`, `get_game_broadcasts()` |
| CDN | `get_cdn_game()`, `get_cdn_scoreboard()` |
| Venues | `get_venues()` |
| Coaches | `get_coaches()`, `get_coach()` |
| Metadata | `get_league_info()` |
| Power Index | `get_power_index()` |
| QBR | `get_qbr()` |

### Database Models

| Model | Key Fields | Updated Via |
|-------|-----------|-------------|
| `Sport` | slug, name | `ingest/teams/` |
| `League` | slug, name, abbreviation | `ingest/teams/` |
| `Team` | espn_id, display_name, logos, color | `ingest/teams/` |
| `Event` | espn_id, date, status, season_year | `ingest/scoreboard/` |
| `Competitor` | team, home_away, score, winner | `ingest/scoreboard/` |
| `Athlete` | espn_id, position, headshot | manual/client |
| `Venue` | espn_id, name, city, capacity | `ingest/scoreboard/` |
| `NewsArticle` | espn_id, headline, published, league | `ingest/news/` |
| `Injury` | athlete_name, status, injury_type, team | `ingest/injuries/` |
| `Transaction` | espn_id, date, description, type | `ingest/transactions/` |
| `AthleteSeasonStats` | athlete_espn_id, season_year, stats (JSON) | `AthleteStatsIngestionService` |

### Celery Beat Schedule

| Task | Frequency |
|------|-----------|
| `refresh_all_news_task` | Every 30 minutes |
| `refresh_all_injuries_task` | Every 4 hours |
| `refresh_all_transactions_task` | Every 6 hours |
| `refresh_scoreboard_task` (NBA/NFL) | Every hour |
| `refresh_all_teams_task` | Weekly |

### Management Commands

```bash
# Ingest news for a single league
python manage.py ingest_news --sport basketball --league nba

# Ingest news for all configured leagues
python manage.py ingest_news

# Refresh injury report for a league
python manage.py ingest_injuries --sport football --league nfl

# Ingest transactions
python manage.py ingest_transactions --sport basketball --league nba

# Ingest all teams (all configured leagues)
python manage.py ingest_all_teams
```

### Docker Testing

```bash
cd espn_service

# Build and run full test suite
docker compose -f docker-compose.test.yml run --rm test

# Run a specific test file
docker compose -f docker-compose.test.yml run --rm test \
  python -m pytest tests/test_ingestion_new.py -v --no-cov
```

### Example Usage

```bash
# Ingest NBA teams
curl -X POST http://localhost:8000/api/v1/ingest/teams/ \
  -H "Content-Type: application/json" \
  -d '{"sport": "basketball", "league": "nba"}'

# Ingest NFL injury report
curl -X POST http://localhost:8000/api/v1/ingest/injuries/ \
  -H "Content-Type: application/json" \
  -d '{"sport": "football", "league": "nfl"}'

# Ingest NBA news (last 25 articles)
curl -X POST http://localhost:8000/api/v1/ingest/news/ \
  -H "Content-Type: application/json" \
  -d '{"sport": "basketball", "league": "nba", "limit": 25}'

# Query injuries by status
curl "http://localhost:8000/api/v1/injuries/?league=nfl&status=out"

# Query latest NBA news
curl "http://localhost:8000/api/v1/news/?league=nba&date_from=2024-01-01"

# Query events
curl "http://localhost:8000/api/v1/events/?league=nfl&date=2024-12-15"
```

See [espn_service/README.md](espn_service/README.md) for full service documentation.

---

## Notable Specialized Endpoints

These endpoints are available but not part of the standard sport-scoped pattern:

### 🏈 QBR (Quarterback Rating)

```bash
# Season QBR by conference
GET https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/{year}/types/{type}/groups/{group}/qbr/{split}

# Weekly QBR
GET https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/{year}/types/{type}/weeks/{week}/qbr/{split}
```

> `split` values: `0` = totals, `1` = home, `2` = away

### 🏀 Bracketology (NCAA Tournament)

```bash
# Live bracket projections
GET https://sports.core.api.espn.com/v2/tournament/{tournamentId}/seasons/{year}/bracketology

# Snapshot at a specific iteration
GET https://sports.core.api.espn.com/v2/tournament/{tournamentId}/seasons/{year}/bracketology/{iteration}
```

### 📊 Power Index (BPI / SP+)

```bash
# Season-level
GET https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/seasons/{year}/powerindex

# Leaders
GET https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/seasons/{year}/powerindex/leaders

# By team
GET https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/seasons/{year}/powerindex/{teamId}
```

### 🎓 Recruiting (College Sports)

```bash
# Recruit rankings by year
GET https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/{year}/recruits

# Recruiting class by team
GET https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/{year}/classes/{teamId}
```

### 👔 Coaches

```bash
# All coaches for a season
GET https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/seasons/{year}/coaches

# Individual coach
GET https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/coaches/{coachId}

# Coach career record by type
GET https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/coaches/{coachId}/record/{type}
```

---

## Contributing

Found a new endpoint? Please open an issue or PR!

## License

MIT License — See LICENSE file

---

*Last Updated: March 2026 · 17 sports · 139 leagues · 370 v2 + 79 v3 endpoints · 6 API domains*

---

# FILE: `docker-compose.yml`

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: espn_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  web:
    build:
      context: ./espn_service
    command: >
      sh -c "python manage.py migrate &&
             python manage.py runserver 0.0.0.0:8000"
    volumes:
      - ./espn_service:/app
    ports:
      - "8000:8000"
    env_file:
      - espn_service/.env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  worker:
    build:
      context: ./espn_service
    command: celery -A config worker --loglevel=info
    volumes:
      - ./espn_service:/app
    env_file:
      - espn_service/.env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  beat:
    build:
      context: ./espn_service
    command: celery -A config beat --loglevel=info
    volumes:
      - ./espn_service:/app
    env_file:
      - espn_service/.env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

volumes:
  postgres_data:

```

---

# FILE: `docs/README.md`

# ESPN API Documentation

> Comprehensive reference for the unofficial ESPN API — endpoints, parameters, league slugs, response schemas, and a working Django service.

---

## 📁 File Index

### Root
| File | Description |
|------|-------------|
| [README.md](../README.md) | Full documentation — base URLs, endpoint patterns, fantasy, betting, specialized endpoints |
| [CHANGELOG.md](../CHANGELOG.md) | History of all documented changes |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | How to contribute endpoints, fixes, and code |

### Sports Reference (`docs/sports/`)

Each file covers leagues & competitions, API endpoints, Site API resources, and curl examples for that sport.

| File | Sport | Key Leagues |
|------|-------|-------------|
| [_global.md](sports/_global.md) | All Sports | Every v2 endpoint — full WADL listing |
| [football.md](sports/football.md) | 🏈 Football | NFL, NCAAF, CFL, UFL, XFL |
| [basketball.md](sports/basketball.md) | 🏀 Basketball | NBA, WNBA, NCAAM, NCAAW, NBL, FIBA |
| [soccer.md](sports/soccer.md) | ⚽ Soccer | EPL, La Liga, Bundesliga, MLS, UCL, 260+ leagues |
| [baseball.md](sports/baseball.md) | ⚾ Baseball | MLB, NCAAB, WBC, Caribbean/Winter Leagues |
| [hockey.md](sports/hockey.md) | 🏒 Hockey | NHL, NCAAH, Olympics |
| [golf.md](sports/golf.md) | ⛳ Golf | PGA TOUR, LPGA, LIV, DP World Tour, TGL |
| [racing.md](sports/racing.md) | 🏎️ Racing | Formula 1, IndyCar, NASCAR Cup/Xfinity/Truck |
| [tennis.md](sports/tennis.md) | 🎾 Tennis | ATP, WTA |
| [mma.md](sports/mma.md) | 🥊 MMA | UFC, Bellator, LFA, and 50+ promotions |
| [rugby.md](sports/rugby.md) | 🏉 Rugby Union | World Cup, Six Nations, Premiership, Super Rugby |
| [rugby_league.md](sports/rugby_league.md) | 🏉 Rugby League | NRL, Super League |
| [lacrosse.md](sports/lacrosse.md) | 🥍 Lacrosse | PLL, NLL, NCAA Men's/Women's |
| [cricket.md](sports/cricket.md) | 🏏 Cricket | ICC T20, ICC ODI, IPL |
| [volleyball.md](sports/volleyball.md) | 🏐 Volleyball | FIVB Men/Women, NCAA Men's/Women's |
| [water_polo.md](sports/water_polo.md) | 🤽 Water Polo | FINA Men/Women, NCAA Men's/Women's |
| [field_hockey.md](sports/field_hockey.md) | 🏑 Field Hockey | FIH Men/Women, NCAA Women's |
| [australian_football.md](sports/australian_football.md) | 🦘 Australian Football | AFL |

### API Reference
| File | Description |
|------|-------------|
| [response_schemas.md](response_schemas.md) | Example JSON responses for scoreboard, teams, roster, injuries, game summary, athlete, odds, standings, Now API |

### Domain Routing Guide

> All domains below were **live-verified via browser HTTP tests on 2026-03-26** — all returned HTTP 200 OK.

| Domain | Use for | Verified Response Keys |
|--------|---------|----------------------|
| `site.api.espn.com/apis/site/v2/` | Scoreboard, teams, news, injuries, transactions, statistics, groups, draft, summary, rankings | `leagues`, `season`, `week`, `events` (scoreboard); `header`, `articles` (news); `uid`, `children` (standings) |
| `site.api.espn.com/apis/v2/` | **Standings only** — site/v2 returns a stub | `uid`, `id`, `name`, `abbreviation`, `children` |
| `site.web.api.espn.com/apis/common/v3/` | Athlete stats, gamelog, overview, splits (`statistics/byathlete`) | `leagues`, `season`, `day`, `events` (same as site.api) |
| `cdn.espn.com/core/` | Full game packages — drives, plays, odds (requires `?xhr=1`) | Varies by sport |
| `now.core.api.espn.com/v1/` | Real-time news feed — filter by `sport=`, `league=`, `team=` | `resultsCount`, `resultsLimit`, `resultsOffset`, `headlines[]` |
| `sports.core.api.espn.com/v2/` | Core data — events, odds, play-by-play, athletes, coaches | Leagues: `$ref`, `id`, `name`, `season`, `teams`, `athletes`; Collections: `count`, `pageIndex`, `pageSize`, `items[]` |

**Sport-specific exceptions:**
- 🏏 **Cricket scoreboard** → core API: `sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/events`
- 🏉 **Rugby Union standings** → core API: `sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/standings`
- ⛳ **Golf / 🎾 Tennis scoreboard** → slug required: `pga`, `lpga`, `atp`, `wta` (not numeric IDs)


---

## 🚀 Quick Links

| Data | Endpoint |
|------|----------|
| Scoreboard | `https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard` |
| Teams | `https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams` |
| Standings | `https://site.api.espn.com/apis/v2/sports/{sport}/{league}/standings` |
| Game summary | `https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={id}` |
| Full game package | `https://cdn.espn.com/core/{sport}/game?xhr=1&gameId={id}` |
| Athlete overview | `https://site.web.api.espn.com/apis/common/v3/sports/{sport}/{league}/athletes/{id}/overview` |
| Athlete stats | `https://site.web.api.espn.com/apis/common/v3/sports/{sport}/{league}/athletes/{id}/stats` |
| Stats leaderboard | `https://site.web.api.espn.com/apis/common/v3/sports/{sport}/{league}/statistics/byathlete` |
| Real-time news | `https://now.core.api.espn.com/v1/sports/news?sport=football` |
| Core API | `https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/...` |


---

# FILE: `docs/response_schemas.md`

# ESPN API Response Schemas

> Example JSON response structures for the most commonly used endpoints.  
> All responses are truncated for brevity — actual responses contain more fields.

---

## Scoreboard (`/apis/site/v2/sports/{sport}/{league}/scoreboard`)

```json
{
  "leagues": [
    {
      "id": "46",
      "name": "National Basketball Association",
      "abbreviation": "NBA",
      "slug": "nba",
      "season": {
        "year": 2025,
        "type": 2,
        "slug": "regular-season"
      },
      "logos": [{ "href": "https://...", "width": 500, "height": 500 }]
    }
  ],
  "events": [
    {
      "id": "401765432",
      "uid": "s:40~l:46~e:401765432",
      "date": "2025-03-15T00:00Z",
      "name": "Boston Celtics at Golden State Warriors",
      "shortName": "BOS @ GSW",
      "season": { "year": 2025, "type": 2, "slug": "regular-season" },
      "week": { "number": 18 },
      "status": {
        "clock": "0.0",
        "displayClock": "0.0",
        "period": 4,
        "type": {
          "id": "3",
          "name": "STATUS_FINAL",
          "state": "post",
          "completed": true,
          "description": "Final",
          "detail": "Final",
          "shortDetail": "Final"
        }
      },
      "competitions": [
        {
          "id": "401765432",
          "attendance": 18064,
          "venue": {
            "id": "1234",
            "fullName": "Chase Center",
            "address": { "city": "San Francisco", "state": "CA" },
            "capacity": 18064,
            "indoor": true
          },
          "broadcasts": [
            {
              "market": { "id": "1", "type": "National" },
              "media": { "shortName": "ESPN" },
              "type": { "id": "1", "shortName": "TV" }
            }
          ],
          "competitors": [
            {
              "id": "17",
              "homeAway": "home",
              "team": {
                "id": "9",
                "uid": "s:40~l:46~t:9",
                "abbreviation": "GSW",
                "displayName": "Golden State Warriors",
                "shortDisplayName": "Warriors",
                "color": "006BB6",
                "alternateColor": "FDB927",
                "logo": "https://..."
              },
              "score": "121",
              "winner": true,
              "records": [{ "name": "overall", "summary": "42-24" }],
              "leaders": [
                {
                  "name": "points",
                  "displayName": "Points Leader",
                  "leaders": [
                    {
                      "displayValue": "32",
                      "athlete": { "id": "3136776", "displayName": "Stephen Curry" }
                    }
                  ]
                }
              ]
            },
            {
              "id": "2",
              "homeAway": "away",
              "team": {
                "id": "2",
                "abbreviation": "BOS",
                "displayName": "Boston Celtics",
                "score": "115",
                "winner": false
              }
            }
          ]
        }
      ]
    }
  ]
}
```

---

## Teams (`/apis/site/v2/sports/{sport}/{league}/teams`)

```json
{
  "sports": [
    {
      "id": "46",
      "name": "Basketball",
      "leagues": [
        {
          "id": "46",
          "name": "NBA",
          "teams": [
            {
              "team": {
                "id": "9",
                "uid": "s:40~l:46~t:9",
                "slug": "golden-state-warriors",
                "abbreviation": "GSW",
                "displayName": "Golden State Warriors",
                "shortDisplayName": "Warriors",
                "name": "Warriors",
                "nickname": "Warriors",
                "location": "Golden State",
                "color": "006BB6",
                "alternateColor": "FDB927",
                "isActive": true,
                "isAllStar": false,
                "logos": [
                  {
                    "href": "https://...",
                    "width": 500,
                    "height": 500,
                    "rel": ["full", "default"]
                  }
                ],
                "links": [
                  {
                    "rel": ["clubhouse"],
                    "href": "https://www.espn.com/nba/team/_/id/9/golden-state-warriors",
                    "text": "Clubhouse"
                  }
                ]
              }
            }
          ]
        }
      ]
    }
  ],
  "count": 30,
  "pageIndex": 1,
  "pageSize": 100
}
```

---

## Team Roster (`/apis/site/v2/sports/{sport}/{league}/teams/{id}/roster`)

```json
{
  "team": {
    "id": "9",
    "abbreviation": "GSW",
    "displayName": "Golden State Warriors"
  },
  "athletes": [
    {
      "position": "G",
      "items": [
        {
          "id": "3136776",
          "uid": "s:40~l:46~a:3136776",
          "guid": "...",
          "firstName": "Stephen",
          "lastName": "Curry",
          "displayName": "Stephen Curry",
          "shortName": "S. Curry",
          "jersey": "30",
          "position": {
            "id": "2",
            "name": "Shooting Guard",
            "displayName": "Shooting Guard",
            "abbreviation": "SG"
          },
          "age": 36,
          "height": 74,
          "weight": 185,
          "birthDate": "1988-03-14",
          "experience": { "years": 15 },
          "status": { "id": "1", "name": "Active", "type": "active" },
          "headshot": { "href": "https://..." }
        }
      ]
    }
  ],
  "coach": [
    {
      "id": "6010",
      "firstName": "Steve",
      "lastName": "Kerr",
      "experience": 10
    }
  ]
}
```

---

## Team Injuries (`/apis/site/v2/sports/{sport}/{league}/teams/{id}/injuries`)

```json
{
  "team": {
    "id": "9",
    "abbreviation": "GSW"
  },
  "injuries": [
    {
      "id": "12345",
      "athlete": {
        "id": "3136776",
        "displayName": "Stephen Curry",
        "position": { "abbreviation": "SG" },
        "headshot": { "href": "https://..." }
      },
      "type": {
        "id": "1",
        "name": "knee",
        "description": "Knee",
        "abbreviation": "KNEE"
      },
      "location": "left knee",
      "detail": "Left knee soreness",
      "side": "left",
      "fantasy": { "status": "doubtful", "injuryType": "KNEE" },
      "status": "Doubtful",
      "date": "2025-03-10T00:00Z"
    }
  ]
}
```

---

## Game Summary (`/apis/site/v2/sports/{sport}/{league}/summary?event={id}`)

```json
{
  "boxscore": {
    "teams": [
      {
        "team": { "id": "9", "displayName": "Golden State Warriors" },
        "statistics": [
          { "name": "assists", "displayValue": "28", "label": "Assists" },
          { "name": "rebounds", "displayValue": "41", "label": "Rebounds" },
          { "name": "fieldGoalPct", "displayValue": "48.5", "label": "FG%" }
        ],
        "players": [
          {
            "team": { "id": "9" },
            "position": { "displayName": "Guard" },
            "statistics": [
              {
                "names": ["MIN", "FG", "3PT", "FT", "OREB", "DREB", "REB", "AST", "STL", "BLK", "TO", "PF", "+/-", "PTS"],
                "athletes": [
                  {
                    "athlete": { "id": "3136776", "displayName": "Stephen Curry" },
                    "didNotPlay": false,
                    "stats": ["36", "12-24", "4-10", "4-4", "0", "5", "5", "7", "1", "0", "2", "2", "+8", "32"]
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  },
  "plays": [
    {
      "id": "4017654340001",
      "sequenceNumber": "1",
      "text": "S. Curry makes 2-pt jump shot from 14 ft",
      "clock": { "displayValue": "11:42" },
      "period": { "number": 1 },
      "team": { "id": "9" },
      "scoreValue": 2,
      "scoringPlay": true
    }
  ],
  "leaders": [
    {
      "name": "points",
      "displayName": "Points Leaders",
      "leaders": [
        {
          "displayValue": "32",
          "team": { "id": "9" },
          "athlete": { "id": "3136776", "displayName": "Stephen Curry" }
        }
      ]
    }
  ],
  "broadcasts": [
    { "market": "national", "names": ["ESPN"] }
  ],
  "predictor": {
    "header": "ESPN BPI Win Probability",
    "homeTeam": {
      "team": { "id": "9" },
      "gameProjection": "63.4",
      "teamChanceLoss": "36.6"
    }
  }
}
```

---

## Athlete (Core API v2)

`GET https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/athletes/{id}`

```json
{
  "id": "3136776",
  "uid": "s:40~l:46~a:3136776",
  "guid": "...",
  "firstName": "Stephen",
  "lastName": "Curry",
  "displayName": "Stephen Curry",
  "shortName": "S. Curry",
  "weight": 185,
  "displayWeight": "185 lbs",
  "height": 74,
  "displayHeight": "6'2\"",
  "age": 36,
  "dateOfBirth": "1988-03-14T00:00Z",
  "birthPlace": { "city": "Charlotte", "state": "NC", "country": "USA" },
  "citizenship": "United States",
  "jersey": "30",
  "active": true,
  "position": {
    "id": "2",
    "name": "Shooting Guard",
    "abbreviation": "SG"
  },
  "linked": true,
  "team": {
    "$ref": "https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/teams/9"
  },
  "experience": { "years": 15 },
  "college": {
    "guid": "...",
    "mascot": "Bulldogs",
    "name": "Davidson"
  },
  "draft": {
    "year": 2009,
    "round": 1,
    "selection": 7
  },
  "headshot": {
    "href": "https://a.espncdn.com/...",
    "alt": "Stephen Curry"
  },
  "statistics": {
    "$ref": "https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/athletes/3136776/statistics"
  }
}
```

---

## Betting Odds (Core API v2)

`GET https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/events/{id}/competitions/{id}/odds`

```json
{
  "count": 3,
  "items": [
    {
      "provider": {
        "id": "41",
        "name": "DraftKings",
        "priority": 1
      },
      "details": "-3.5",
      "overUnder": 222.5,
      "spread": -3.5,
      "overOdds": -110,
      "underOdds": -110,
      "awayTeamOdds": {
        "favorite": false,
        "underdog": true,
        "moneyLine": 140,
        "spreadOdds": -110
      },
      "homeTeamOdds": {
        "favorite": true,
        "underdog": false,
        "moneyLine": -165,
        "spreadOdds": -110
      },
      "open": {
        "over": { "value": 220.0 },
        "under": { "value": 220.0 },
        "spread": { "home": { "line": -4.5 } }
      }
    }
  ]
}
```

---

## Win Probabilities (Core API v2)

`GET .../events/{id}/competitions/{id}/probabilities`

```json
{
  "count": 1,
  "items": [
    {
      "homeWinPercentage": 0.634,
      "awayWinPercentage": 0.366,
      "tiePercentage": 0.0,
      "lastModified": "2025-03-15T02:14:00Z",
      "play": {
        "$ref": "https://sports.core.api.espn.com/v2/..."
      }
    }
  ]
}
```

---

## Standings (`/apis/site/v2/sports/{sport}/{league}/standings`)

```json
{
  "uid": "s:40~l:46",
  "season": { "year": 2025, "displayName": "2024-25" },
  "fullViewLink": { "href": "https://www.espn.com/nba/standings" },
  "children": [
    {
      "name": "Eastern Conference",
      "abbreviation": "EAST",
      "standings": {
        "entries": [
          {
            "team": {
              "id": "2",
              "uid": "s:40~l:46~t:2",
              "displayName": "Boston Celtics",
              "abbreviation": "BOS",
              "logo": "https://..."
            },
            "note": { "color": "03A653", "description": "Clinched Playoffs" },
            "stats": [
              { "name": "wins", "displayName": "Wins", "displayValue": "52" },
              { "name": "losses", "displayName": "Losses", "displayValue": "14" },
              { "name": "winPercent", "displayName": "PCT", "displayValue": ".788" },
              { "name": "gamesBehind", "displayName": "GB", "displayValue": "-" },
              { "name": "streak", "displayName": "Strk", "displayValue": "W3" }
            ]
          }
        ]
      }
    }
  ]
}
```

---

## Now API News (`now.core.api.espn.com/v1/sports/news`)

```json
{
  "resultsCount": 1000,
  "resultsLimit": 20,
  "resultsOffset": 0,
  "feed": [
    {
      "dataSourceIdentifier": "espn_wire_12345",
      "description": "Stephen Curry scores 32 points as Golden State Warriors beat Boston Celtics",
      "nowId": "11-12345",
      "premium": false,
      "published": "2025-03-15T02:00:00Z",
      "lastModified": "2025-03-15T02:30:00Z",
      "type": "HeadlineNews",
      "headline": "Curry scores 32, Warriors top Celtics",
      "links": {
        "web": { "href": "https://www.espn.com/nba/story/_/id/12345" },
        "api": { "href": "https://api.espn.com/v1/sports/news/12345" }
      },
      "images": [
        {
          "id": 98765,
          "name": "stephen-curry.jpg",
          "url": "https://a.espncdn.com/photo/...",
          "width": 576,
          "height": 324
        }
      ],
      "categories": [
        { "type": "league", "id": 46, "description": "NBA" },
        { "type": "team", "id": 9, "description": "Golden State Warriors" },
        { "type": "athlete", "id": 3136776, "description": "Stephen Curry" }
      ]
    }
  ]
}
```

---

## CDN Game Package (`cdn.espn.com/core/{sport}/{endpoint}?xhr=1`)

> Returns a large `gamepackageJSON` object containing all game data. Requires `?xhr=1`.

```bash
curl "https://cdn.espn.com/core/nfl/game?xhr=1&gameId=401671793"
```

```json
{
  "gameId": "401671793",
  "gamepackageJSON": {
    "header": {
      "id": "401671793",
      "season": { "year": 2025, "type": 3 },
      "competitions": [
        {
          "id": "401671793",
          "competitors": [
            { "id": "12", "homeAway": "home", "score": "27", "winner": true },
            { "id": "25", "homeAway": "away", "score": "24", "winner": false }
          ],
          "status": {
            "type": { "name": "STATUS_FINAL", "state": "post", "completed": true }
          }
        }
      ]
    },
    "boxscore": { "teams": [], "players": [] },
    "drives": {
      "previous": [
        {
          "id": "4016717931\",",
          "description": "10 plays, 75 yards, 4:32",
          "team": { "id": "12" },
          "plays": [ { "id": "...", "type": { "text": "Rush" }, "text": "..." } ],
          "result": "Touchdown",
          "yards": 75
        }
      ]
    },
    "plays": [ { "id": "...", "text": "...", "scoringPlay": true } ],
    "winprobability": [ { "homeWinPercentage": 0.72, "playId": "..." } ],
    "news": { "articles": [] },
    "standings": {}
  }
}
```

---

## Athlete Overview (`site.web.api.espn.com/apis/common/v3/sports/{sport}/{league}/athletes/{id}/overview`)

> Works for NFL, NBA, NHL, MLB. Response includes stats snapshot, next game, recent news, and rotowire notes.

```json
{
  "statistics": {
    "labels": ["GP", "PTS", "REB", "AST"],
    "names": ["gamesPlayed", "avgPoints", "avgRebounds", "avgAssists"],
    "values": [56.0, 26.4, 4.5, 6.1],
    "displayValues": ["56", "26.4", "4.5", "6.1"]
  },
  "news": { "articles": [ { "headline": "...", "published": "2025-03-14T21:00Z" } ] },
  "nextGame": {
    "id": "401765999",
    "date": "2025-03-16T17:30Z",
    "name": "Golden State Warriors at Boston Celtics",
    "competitions": []
  },
  "gameLog": {
    "events": [
      { "id": "401765000", "gameResult": "W", "stats": ["34", "5", "7"] }
    ]
  },
  "rotowire": { "injury": null, "news": "Curry is healthy and expected to play Friday." }
}
```

---

## Athlete Stats (`site.web.api.espn.com/apis/common/v3/sports/{sport}/{league}/athletes/{id}/stats`)

> Works for NFL, NBA, NHL, MLB. Soccer uses a different path.

```json
{
  "filters": [
    {
      "displayName": "Season Type",
      "name": "seasontype",
      "value": "2",
      "options": [
        { "value": "2", "displayValue": "Regular Season" },
        { "value": "3", "displayValue": "Playoffs" }
      ]
    }
  ],
  "teams": [
    { "id": "9", "uid": "s:40~l:46~t:9", "displayName": "Golden State Warriors" }
  ],
  "categories": [
    {
      "name": "general",
      "displayName": "General",
      "labels": ["GP", "GS", "MIN", "PTS", "REB", "AST", "STL", "BLK", "TO", "FG%", "3P%", "FT%"],
      "totals": ["56", "56", "34.2", "26.4", "4.5", "6.1", "0.9", "0.4", "3.1", ".502", ".408", ".924"]
    }
  ],
  "glossary": [
    { "abbreviation": "GP", "displayName": "Games Played", "description": "Total games played" }
  ]
}
```

---

## Athlete Gamelog (`site.web.api.espn.com/apis/common/v3/sports/{sport}/{league}/athletes/{id}/gamelog`)

```json
{
  "filters": [ { "displayName": "Season", "name": "season", "value": "2025" } ],
  "labels": ["DATE", "OPP", "RESULT", "MIN", "FG", "3PT", "FT", "REB", "AST", "STL", "BLK", "PTS"],
  "names": ["date", "opponent", "gameResult", "minutes", "fieldGoalsMade", "threePointsMade", "freeThrowsMade", "rebounds", "assists", "steals", "blocks", "points"],
  "displayNames": ["Date", "OPP", "RESULT", "MIN", "FG", "3PT", "FT", "REB", "AST", "STL", "BLK", "PTS"],
  "events": [
    {
      "id": "401765000",
      "date": "2025-03-14T00:00Z",
      "opponent": { "id": "2", "displayName": "Boston Celtics", "abbreviation": "BOS" },
      "gameResult": "W",
      "stats": ["36", "12-24", "4-10", "4-4", "5", "7", "1", "0", "32"]
    }
  ]
}
```

---

## Athlete Splits (`site.web.api.espn.com/apis/common/v3/sports/{sport}/{league}/athletes/{id}/splits`)

```json
{
  "filters": [ { "displayName": "Season Type", "name": "seasontype" } ],
  "displayName": "Stephen Curry",
  "categories": [
    {
      "name": "home",
      "displayName": "Home",
      "labels": ["GP", "PTS", "REB", "AST"],
      "totals": ["28", "27.1", "4.8", "6.4"]
    },
    {
      "name": "away",
      "displayName": "Away",
      "labels": ["GP", "PTS", "REB", "AST"],
      "totals": ["28", "25.7", "4.2", "5.8"]
    }
  ]
}
```

---

## Statistics by Athlete (`site.web.api.espn.com/apis/common/v3/sports/{sport}/{league}/statistics/byathlete`)

> Statistical leaderboard across all athletes. Works for NBA, NFL, MLB, NHL.

```bash
curl "https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/statistics/byathlete"
curl "https://site.web.api.espn.com/apis/common/v3/sports/baseball/mlb/statistics/byathlete?category=batting&sort=batting.homeRuns:desc&season=2024"
```

```json
{
  "pagination": { "count": 500, "limit": 50, "page": 1, "pages": 10 },
  "league": { "id": "46", "name": "NBA" },
  "currentSeason": { "year": 2025, "type": 2 },
  "athletes": [
    {
      "athlete": {
        "id": "3136776",
        "displayName": "Stephen Curry",
        "team": { "id": "9", "abbreviation": "GSW" },
        "position": { "abbreviation": "PG" }
      },
      "statistics": [
        { "name": "avgPoints", "displayValue": "26.4", "rank": 5 }
      ]
    }
  ]
}
```

---

## League-wide Injuries (`/apis/site/v2/sports/{sport}/{league}/injuries`)

> Works for team sports: NBA, NFL, NHL, MLB, Soccer. Returns 500 for MMA, Tennis, Golf.

```json
{
  "timestamp": "2025-03-23T12:00:00Z",
  "status": "success",
  "season": { "year": 2025, "type": 2 },
  "injuries": [
    {
      "team": {
        "id": "9",
        "displayName": "Golden State Warriors",
        "abbreviation": "GSW"
      },
      "injuries": [
        {
          "id": "12345",
          "athlete": {
            "id": "3136776",
            "displayName": "Stephen Curry",
            "position": { "abbreviation": "PG" }
          },
          "type": { "name": "knee" },
          "status": "Day-To-Day",
          "date": "2025-03-20T00:00Z"
        }
      ]
    }
  ]
}
```

---

## Transactions (`/apis/site/v2/sports/{sport}/{league}/transactions`)

```json
{
  "timestamp": "2025-03-23T12:00:00Z",
  "status": "success",
  "season": { "year": 2025, "type": 2 },
  "requestedYear": 2025,
  "count": 42,
  "transactions": [
    {
      "id": "99001",
      "date": "2025-03-20T00:00Z",
      "description": "GSW signed F Joe Smith to a 10-day contract",
      "team": { "id": "9", "displayName": "Golden State Warriors" },
      "type": { "id": "1", "description": "Contract Signing" }
    }
  ]
}
```

---

## Groups / Conferences (`/apis/site/v2/sports/{sport}/{league}/groups`)

```json
{
  "status": "success",
  "groups": [
    {
      "id": "5",
      "name": "Eastern Conference",
      "abbreviation": "East",
      "children": [
        { "id": "1", "name": "Atlantic Division", "abbreviation": "Atlantic" },
        { "id": "2", "name": "Central Division", "abbreviation": "Central" },
        { "id": "3", "name": "Southeast Division", "abbreviation": "Southeast" }
      ]
    },
    {
      "id": "6",
      "name": "Western Conference",
      "abbreviation": "West"
    }
  ]
}
```

---

## Rankings (`/apis/site/v2/sports/{sport}/{league}/rankings`)

> Works for college sports: `college-football`, `mens-college-basketball`.

```bash
curl "https://site.api.espn.com/apis/site/v2/sports/football/college-football/rankings"
curl "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/rankings"
```

```json
{
  "sports": [ { "id": "23", "name": "College Football" } ],
  "leagues": [ { "id": "23", "name": "NCAA Football" } ],
  "rankings": [
    {
      "name": "AP Top 25",
      "shortName": "AP Poll",
      "type": "ap",
      "occurrence": { "number": 13, "value": 13, "displayValue": "Week 13" },
      "ranks": [
        {
          "current": 1,
          "previous": 1,
          "points": 1575,
          "firstPlaceVotes": 63,
          "team": {
            "id": "333",
            "displayName": "Alabama Crimson Tide",
            "abbreviation": "ALA",
            "record": { "summary": "11-0" }
          }
        }
      ]
    }
  ],
  "latestWeek": { "number": 13, "startDate": "2024-11-11" }
}
```

---

# FILE: `docs/sports/_global.md`

# 🌐 Global & Generic Endpoints

These endpoints are not sport-scoped and apply across the entire ESPN API.

**Base URL (v2):** `https://sports.core.api.espn.com/v2`  
**Base URL (v3):** `https://sports.core.api.espn.com/v3`

---

## 🚀 Quick Reference

The most useful cross-sport global endpoints — great starting points for exploration.

### Discovery

```bash
# List all sports tracked by ESPN
curl "https://sports.core.api.espn.com/v2/sports"

# List all leagues (cross-sport)
curl "https://sports.core.api.espn.com/v2/ontology/leagues?limit=500"

# List all teams (cross-sport)
curl "https://sports.core.api.espn.com/v2/ontology/teams?limit=500"

# List all sports via v3
curl "https://sports.core.api.espn.com/v3/sports"

# List all leagues via v3
curl "https://sports.core.api.espn.com/v3/leagues?limit=500"
```

### Cross-Sport Athletes & Coaches

```bash
# Look up athlete by ESPN ID (v3)
curl "https://sports.core.api.espn.com/v3/athletes/{athleteId}"

# Athlete event log
curl "https://sports.core.api.espn.com/v3/{athlete}/eventlog"

# Coach lookup
curl "https://sports.core.api.espn.com/v3/coaches/{coachId}"
```

### Teams (cross-sport, v3)

```bash
# All teams (cross-sport)
curl "https://sports.core.api.espn.com/v3/teams?limit=1000"

# Single team by ID
curl "https://sports.core.api.espn.com/v3/teams/{teamId}"

# Team depth charts
curl "https://sports.core.api.espn.com/v3/teams/{teamId}/depthcharts"

# Team schedule / events
curl "https://sports.core.api.espn.com/v3/teams/{teamId}/events"
```

### Global Events & Games

```bash
# All events
curl "https://sports.core.api.espn.com/v3/events?limit=100&dates=20250915"

# Single event by ID
curl "https://sports.core.api.espn.com/v3/events/{eventId}"

# Play-by-play
curl "https://sports.core.api.espn.com/v3/events/{eventId}/competitions/{compId}/plays"
```

### Odds, Predictions & Power Index (v3)

```bash
# Global odds
curl "https://sports.core.api.espn.com/v3/odds"

# Win predictions
curl "https://sports.core.api.espn.com/v3/predictions"

# Power index
curl "https://sports.core.api.espn.com/v3/powerindex"

# Global standings
curl "https://sports.core.api.espn.com/v3/standings"
```

### API Meta

```bash
# ESPN API listing / documentation
curl "https://sports.core.api.espn.com/v2/api-docs"

# WADL schema
curl "https://sports.core.api.espn.com/v3application.wadl"
```

---

## V2 Global Endpoints

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/api-docs` | `getApiListings` | — |
| `https://sports.core.api.espn.com/v2/athletes` | `getDraftAthletes` | `page`, `limit`, `available`, `position`, `team`, `sort`, `filter` |
| `https://sports.core.api.espn.com/v2/athletes/{draftAthlete}` | `getDraftAthlete` | `page`, `limit`, `available`, `position`, `team`, `sort`, `filter` |
| `https://sports.core.api.espn.com/v2/colleges` | `getColleges` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/commentaries` | `getCommentaries` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/commentaries/{commentaryId}` | `getCommentary` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/commentaries/{commentaryId}/comments` | `getCommentaryComments` | `sort`, `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/commentaries/{commentaryId}/comments/{commentaryCommentId}` | `getCommentaryComment` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/competitions` | `getCompetitions` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/competitions/{competitionId}` | `getCompetition` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/competitors` | `getCompetitors` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/courses/{courseId}` | `getEventCourse` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/courses/{courseId}/rounds/{roundNumber}/statistics` | `getEventCoursesStatisticsByRound` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/disciplines/{discId}` | `getDiscipline` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/drives` | `getDrives` | `period`, `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/drives/{drive}` | `getDrive` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/drives/{drive}/plays` | `getPlays` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/events` | `getSpadeEvents` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/events/{eventId}` | `getSpadeEvent` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/events/{eventId}/competitions` | `getSpadeCompetitions` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/events/{eventId}/competitions/{competitionId}` | `getSpadeCompetition` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/events/{eventId}/competitions/{competitionId}/athletes/{athleteId}` | `getSpadeAthlete` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/events/{eventId}/competitions/{competitionId}/competitors` | `getSpadeCompetitors` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/events/{eventId}/competitions/{competitionId}/competitors/{competitorId}` | `getSpadeCompetitor` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/events/{eventId}/competitions/{competitionId}/competitors/{competitorId}/linescores` | `getSpadeCompetitorLinescore` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/events/{eventId}/competitions/{competitionId}/competitors/{competitorId}/roster` | `getSpadeCompetitorRoster` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/events/{eventId}/competitions/{competitionId}/competitors/{competitorId}/roster/{athleteId}/statistics` | `getSpadeCompetitorRosterStatistics` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/events/{eventId}/competitions/{competitionId}/competitors/{competitorId}/score` | `getSpadeCompetitorScore` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/events/{eventId}/competitions/{competitionId}/competitors/{competitorId}/statistics` | `getSpadeCompetitorStatistics` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/events/{eventId}/competitions/{competitionId}/competitors/{competitorId}/status` | `getSpadeCompetitorStatus` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/events/{eventId}/competitions/{competition}/plays` | `getSpadePlays` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/export` | `getExportFile` | — |
| `https://sports.core.api.espn.com/v2/faux` | `getFauxResponse` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/items` | `getShopItems` | `guids`, `source`, `type`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/items/{id}` | `getShopItem` | `source`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/lastPlay` | `getLastPlay` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/leaders` | `getLeadersByGame` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/linescores` | `getLinescores` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/linescores/{sourceId}` | `getLinescoresBySource` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/linescores/{sourceId}/{period}` | `getLinescoreBySourcePeriod` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/manufacturers/{manufacturer}/statistics` | `getManufacturerCompetitionStats` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/manufacturers/{manufacturer}/statistics/{split}` | `getManufacturerCompetitionStats` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/notes` | `getEventNotes` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/objects` | `getObjects` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/odds/{oddsId}/similarities` | `getSimilaritiesOdds` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/olympics` | `getOlympicTypes` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/ontology/competitions` | `getCompetitions` | `discovery`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/ontology/events` | `getEvents` | `discovery`, `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/ontology/leagues` | `getLeagues` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/ontology/schools` | `getSchools` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/ontology/sports` | `getSports` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/ontology/teams` | `getTeams` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/ontology/venues` | `getVenues` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/plays` | `getPlays` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/plays/{playId}/participants/{participantId}/statistics/{splitType}` | `getPlayerPlayStatsByPlayerPlay` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/plays/{playId}/teams/{teamId}/statistics/{splitType}` | `getTeamPlayStatsByTeamPlay` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/plays/{play}` | `getPlay` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/plays/{source}/play/{play}` | `getPlayBySource` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/powerindex` | `getPowerIndexSeasons` | `groupId`, `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/powerindex/{team}` | `getPowerIndexByTeamGame` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/predictor` | `getGamePredictor` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/probabilities` | `getProbabilities` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/probabilities/{playId}` | `getProbability` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/ranks` | `getTeamRankings` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/records` | `getCompetitorRecordForGame` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/records/{split}` | `getCompetitorRecordForGameBySplit` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/recreation/{recreation}` | `getRecreation` | `_sw`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/recreation/{recreation}/teams/{teamId}` | `getRecreationTeams` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/relevancy` | `getCompetitionRelevancy` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/roster` | `getCompetitorRoster` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/roster/{athlete}` | `getCompetitorRosterByPlayer` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/roster/{athlete}/statistics/{split}` | `getPlayerGameStatsByPlayerGame` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/rounds` | `getDraftRounds` | `team`, `page`, `limit`, `available`, `position`, `team`, `sort`, `filter` |
| `https://sports.core.api.espn.com/v2/rounds/{round}/picks/{pick}` | `getDraftPick` | `page`, `limit`, `available`, `position`, `team`, `sort`, `filter` |
| `https://sports.core.api.espn.com/v2/schema` | `generateSchema` | `type`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/score` | `getScore` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/scores` | `getScores` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/scores/{source}` | `getScoreBySource` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/situation` | `getCompetitionSituation` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/spade/{sport}/leagues/{league}` | `getSpadeService` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports` | `getSports` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/statistics` | `getCompetitionStatistics` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/statistics/{split}` | `getTeamGameStatsByTeamGame` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/status` | `getDraftStatus` | `page`, `limit`, `available`, `position`, `team`, `sort`, `filter` |
| `https://sports.core.api.espn.com/v2/tickets` | `getTickets` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/tickets/{ticketid}` | `getTicketsById` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/venues` | `getEventVenues` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/venues/{venueId}` | `getVenue` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/zip/{zip}` | `getWeatherForZip` | `date`, `hour`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{api}` | `getApiDeclaration` | — |
| `https://sports.core.api.espn.com/v2/{athlete}` | `getAthlete` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/{athlete}/awards` | `getAwards` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/{athlete}/competitions` | `getCompetitions` | `types`, `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/{athlete}/contract` | `getCurrentContract` | `page`, `limit`, `seasontypes`, `played`, `teamtypes`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/{athlete}/contracts` | `getContracts` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/{athlete}/contracts/{year}` | `getContract` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/{athlete}/eventlog` | `getEventLog` | `types`, `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/{athlete}/events` | `getEvents` | `page`, `limit`, `seasontypes`, `played`, `teamtypes`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/{athlete}/hotzones` | `getPlayerHitZones` | `season`, `seasontypes`, `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/{athlete}/injuries` | `getInjuries` | `dates`, `page`, `limit`, `seasontypes`, `played`, `teamtypes`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/{athlete}/injuries/{injury}` | `getInjury` | `page`, `limit`, `seasontypes`, `played`, `teamtypes`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/{athlete}/leagues` | `getPlayerLeagues` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `sort`, `type`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/{athlete}/notes` | `getAthleteNotes` | `page`, `limit`, `seasontypes`, `played`, `teamtypes`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/{athlete}/ranks` | `getPlayerRanks` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `sort`, `type`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/{athlete}/ranks/{rankingTypeId}` | `getPlayerRankings` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/{athlete}/records` | `getCareerRecord` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/{athlete}/records/{split}` | `getCareerRecord` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/{athlete}/seasons` | `getPlayerSeasons` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/{athlete}/statistics` | `getCareerStatistics` | `seasonType`, `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/{athlete}/statistics/{split}` | `getCareerStatistics` | `seasonType`, `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/{athlete}/statisticslog` | `getAthleteStatisticsLog` | `seasonType`, `seasontypes`, `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/{athlete}/statisticslog/{split}` | `getAthleteStatisticsLog` | `seasonType`, `seasontypes`, `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/{athlete}/transactions` | `getPlayerTransactions` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `sort`, `type`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/{athlete}/vsathlete/{opponentId}` | `getPlayerVsPlayerCareerStats` | `seasontypes`, `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/{calendarType}` | `getCalendar` | `page`, `limit`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{circuit}` | `getVenue` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{college}` | `getCollege` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{guid}` | `getTeamByGuid` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{guid}/broadcasts` | `getCompetitionBroadcastsByGuid` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{guid}/leagues` | `getLeaguesBySport` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{guid}/teams` | `getTeamsByLeague` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{id}` | `getCasino` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{id}/athletes` | `getAthletesByTeam` | `page`, `limit`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses` |
| `https://sports.core.api.espn.com/v2/{id}/awards` | `getFranchiseAwards` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{id}/calendar` | `getCalendars` | `page`, `limit`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses` |
| `https://sports.core.api.espn.com/v2/{id}/categories` | `getContentCategories` | `site`, `_cc`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{id}/eventlog` | `getManufacturerEventLog` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{id}/head-to-heads` | `getHeadToHeadsOdds` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{id}/history/{type}` | `getTournamentHistoryByTeamByType` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{id}/leagues` | `getLeagues` | `page`, `limit`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses` |
| `https://sports.core.api.espn.com/v2/{id}/odds/{oddsProvider}/past-performances` | `getTeamPastPerformance` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{id}/predictors` | `getPredictors` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{id}/propBets` | `getPropBets` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{league}` | `getLeague` | `page`, `limit`, `profile`, `dates`, `active`, `classId`, `dates`, `sort`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/{league}/awards` | `getLeagueAwards` | `winnertype`, `page`, `limit`, `profile`, `dates`, `active`, `classId`, `dates`, `sort`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/{league}/awards/{award}` | `getAwards` | `winnertype`, `page`, `limit`, `profile`, `dates`, `active`, `classId`, `dates`, `sort`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/{league}/bet-types/{betTypeId}` | `getBetType` | `page`, `limit`, `profile`, `dates`, `active`, `classId`, `dates`, `sort`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/{league}/coaches/{coach}` | `getCareerCoach` | `page`, `limit`, `profile`, `dates`, `active`, `classId`, `dates`, `sort`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/{league}/coaches/{coach}/record/{type}` | `getCoachCareerRecordByType` | `page`, `limit`, `profile`, `dates`, `active`, `classId`, `dates`, `sort`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/{league}/draft` | `getDraft` | `page`, `limit`, `profile`, `dates`, `active`, `classId`, `dates`, `sort`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/{league}/events` | `getEvents` | `bpi`, `page`, `limit`, `profile`, `dates`, `active`, `classId`, `dates`, `sort`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/{league}/groups/{group}` | `getGroup` | `page`, `limit`, `profile`, `dates`, `active`, `classId`, `dates`, `sort`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/{league}/leaders` | `getLeaders` | `page`, `limit`, `profile`, `dates`, `active`, `classId`, `dates`, `sort`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/{league}/leaders/{split}` | `getLeaders` | `page`, `limit`, `profile`, `dates`, `active`, `classId`, `dates`, `sort`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/{league}/meta` | `getMeta` | `enable`, `page`, `limit`, `profile`, `dates`, `active`, `classId`, `dates`, `sort`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/{league}/notes` | `getAthleteNotes` | `page`, `limit`, `profile`, `dates`, `active`, `classId`, `dates`, `sort`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/{league}/qbr/{split}` | `getAllTimeQBR` | `qualified`, `sort`, `group`, `seasonType`, `page`, `limit`, `profile`, `dates`, `active`, `classId`, `dates`, `sort`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/{league}/recruits` | `getRecruitsByLeague` | `page`, `limit`, `profile`, `dates`, `active`, `classId`, `dates`, `sort`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/{league}/recruits/{recruit}` | `getRecruit` | `page`, `limit`, `profile`, `dates`, `active`, `classId`, `dates`, `sort`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/{league}/standings` | `getCurrentStandings` | `page`, `limit`, `profile`, `dates`, `active`, `classId`, `dates`, `sort`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/{league}/standings/season/{season}` | `getCurrentStandings` | `page`, `limit`, `profile`, `dates`, `active`, `classId`, `dates`, `sort`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/{league}/statistics` | `getStatistics` | `sort`, `page`, `limit`, `profile`, `dates`, `active`, `classId`, `dates`, `sort`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/{league}/statistics/{split}/byathlete` | `getPlayerCareerStatsByAthlete` | `page`, `limit`, `profile`, `dates`, `active`, `classId`, `dates`, `sort`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/{league}/talentpicks` | `getPicks` | `page`, `limit`, `profile`, `dates`, `active`, `classId`, `dates`, `sort`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/{league}/transactions` | `getTransactions` | `page`, `limit`, `profile`, `dates`, `active`, `classId`, `dates`, `sort`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/{objectType}` | `getObjectType` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{objectType}/{objectKey}` | `getObjectByKey` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{oddId}/history/{betType}` | `getCompetitionOddsHistory` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{oddId}/history/{betType}/movement` | `getCompetitionOddsHistoryMovement` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{olympicsType}` | `getSeasons` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}` | `getSeason` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/athletes` | `getAthletesBySeason` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/athletes/{athleteId}` | `getAthlete` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/athletes/{athleteId}/competitions` | `getAthleteEvents` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/calendar` | `getCalendars` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/calendar/{calendarType}` | `getCalendar` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/competitions` | `getCompetitionsBySeason` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/countries` | `getCountriesBySeason` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/countries/{countryId}` | `getCountryBySeason` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/countries/{countryId}/competitions` | `getCountryEvents` | `filter`, `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/medals/athletes` | `getMedalsByAthlete` | `sort`, `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/medals/countries` | `getMedalsByCountry` | `sort`, `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/sports` | `getSports` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/sports/{sportId}` | `getSport` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/sports/{sportId}/competitions` | `getCompetitionsBySport` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/sports/{sportId}/disciplines` | `getDisciplinesBySport` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/sports/{sportId}/disciplines/{discId}` | `getDisciplineBySport` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/sports/{sportId}/disciplines/{discId}/calendar` | `getCalendars` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/sports/{sportId}/disciplines/{discId}/calendar/{calendarType}` | `getCalendar` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/sports/{sportId}/disciplines/{discId}/competitions` | `getCompetitionsByDiscipline` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/sports/{sportId}/disciplines/{discId}/events` | `getEventsByDiscipline` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/sports/{sportId}/disciplines/{discId}/events/{eventId}` | `getEvent` | `dates`, `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/sports/{sportId}/disciplines/{discId}/events/{eventId}/competitions` | `getCompetitionsByEvent` | `dates`, `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/sports/{sportId}/disciplines/{discId}/events/{eventId}/competitions/{competitionId}` | `getCompetition` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/sports/{sportId}/disciplines/{discId}/events/{eventId}/competitions/{competitionId}/results` | `getCompetitionResultsByCompetition` | `topTen`, `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/sports/{sportId}/disciplines/{discId}/events/{eventId}/competitions/{competitionId}/results/{sequenceNum}` | `getCompetition` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/sports/{sportId}/disciplines/{discId}/events/{eventId}/standings` | `getStandingsByEvent` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/sports/{sportId}/disciplines/{discId}/events/{eventId}/teams` | `getTeamsByEvent` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/sports/{sportId}/disciplines/{discId}/events/{eventId}/teams/{teamId}` | `getTeamsByEvent` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/sports/{sportId}/disciplines/{discId}/events/{eventId}/teams/{teamId}/standings` | `getTeamStandingsByEvent` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{olympicsType}/{season}/types/{type}` | `getSeasonType` | `page`, `limit`, `dates`, `filter`, `country`, `discId`, `utcOffset`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{provider}` | `getProvider` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{season}` | `getRecruitingSeason` | `page`, `limit`, `sort`, `position`, `status` |
| `https://sports.core.api.espn.com/v2/{season}/athletes` | `getRecruitingAthletes` | `page`, `limit`, `sort`, `position`, `status` |
| `https://sports.core.api.espn.com/v2/{season}/awards` | `getAwardsBySeason` | `winnertype`, `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/awards/{award}` | `getAwardBySeason` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/classes/{team}` | `getRecruitingClass` | `page`, `limit`, `sort`, `position`, `status` |
| `https://sports.core.api.espn.com/v2/{season}/coaches` | `getCoaches` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/coaches/{coach}` | `getSeasonCoach` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/corrections` | `getStatCorrections` | `date`, `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/futures` | `getFutures` | `active`, `groupId`, `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/futures/{futureId}` | `getFuture` | `active`, `sort`, `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/players/{player}/rank` | `getPlayerRanking` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/players/{player}/ranks` | `getPlayerRankings` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/playoff-machine` | `getPlayoffMachine` | `events`, `results`, `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/powerindex` | `getPowerIndexBySeason` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/powerindex/leaders` | `getPowerIndexLeadersBySeason` | `groupId`, `leaderLimit`, `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/powerindex/{team}` | `getPowerIndexByTeamSeason` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/rankings` | `getRecruitingRankingTypes` | `page`, `limit`, `sort`, `position`, `status` |
| `https://sports.core.api.espn.com/v2/{season}/rankings/{id}/dates` | `getRankingsForDate` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/rankings/{id}/dates/{date}` | `getRankingTypeForDate` | `limit`, `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/rankings/{poll}` | `getAvailableSeasonRankingsByPoll` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/rankings/{type}` | `getRecruitingRankingType` | `page`, `limit`, `sort`, `position`, `status` |
| `https://sports.core.api.espn.com/v2/{season}/rankings/{type}/dates` | `getRecruitingRankingDates` | `page`, `limit`, `sort`, `position`, `status` |
| `https://sports.core.api.espn.com/v2/{season}/rankings/{type}/dates/{date}` | `getRecruitingRankingsByDate` | `page`, `limit`, `sort`, `position`, `status` |
| `https://sports.core.api.espn.com/v2/{season}/recruits` | `getRecruitsByYear` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/summary` | `getLeagueSeasonSummary` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/talentpickers` | `getTalentPickers` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/teams` | `getTeamsBySeason` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/teams/{id}/injuries/{injuryId}` | `getInjury` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/teams/{team}` | `getTeamBySeason` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/teams/{team}/athletes` | `getTeamAthletes` | `active`, `position`, `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/teams/{team}/awards` | `getAwardsBySeasonTeam` | `winnertype`, `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/teams/{team}/coaches` | `getCoaches` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/teams/{team}/depthcharts` | `getTeamDepthCharts` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/teams/{team}/events` | `getTeamEventsBySeason` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/teams/{team}/projection` | `getTeamProjection` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/teams/{team}/rank` | `getTeamRanking` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/teams/{team}/ranks` | `getTeamRankings` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/teams/{team}/recruits` | `getRecruitsByTeamYear` | `types`, `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/teams/{team}/summary` | `getTeamSeasonSummary` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/teams/{team}/transactions` | `getTeamTransactions` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/tournaments/{tournament}` | `getTournamentSeason` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/transactions` | `getTransactions` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types` | `getSeasonTypes` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}` | `getSeasonTypes` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/athletes/{athlete}/projections` | `getPlayerSeasonProjectedStatsByPlayerSeason` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/athletes/{athlete}/records/{split}` | `getAthleteRecordBySplit` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/athletes/{athlete}/statistics` | `getPlayerSeasonStatsByPlayerSeason` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/athletes/{athlete}/statistics/{split}` | `getPlayerSeasonStatsByPlayerSeason` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/athletes/{athlete}/vsathlete/{opponentId}` | `getPlayerVsPlayerSeasonStatsByPlayerSeason` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/calendar` | `getCalendars` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/calendar/{calendarType}` | `getCalendar` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/coaches/{coach}/record` | `getCoachSeasonRecord` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/corrections` | `getStatCorrections` | `date`, `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/events` | `getSeasonEvents` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/group` | `getGroup` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/groups` | `getGroups` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/groups/{group}` | `getGroup` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/groups/{group}/athletes/{athlete}/statistics` | `getPlayerSeasonStatsByPlayerGroupSeason` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/groups/{group}/athletes/{athlete}/statistics/{split}` | `getPlayerSeasonStatsByPlayerGroupSeason` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/groups/{group}/calendar` | `getGroupCalendars` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/groups/{group}/calendar/{calendarType}` | `getGroupCalendars` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/groups/{group}/children` | `getGroups` | `conference`, `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/groups/{group}/events` | `getGroupEvents` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/groups/{group}/leaders` | `getLeadersByGroup` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/groups/{group}/qbr/{split}` | `getSeasonQBR` | `qualified`, `sort`, `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/groups/{group}/standings` | `getStandings` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/groups/{group}/standings/{standingType}` | `getStandings` | `month`, `dates`, `live`, `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/groups/{group}/standings/{standingType}/teams/{team}` | `getStandingsForTeam` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/groups/{group}/statistics` | `getGroupStatistics` | `sort`, `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/groups/{group}/statistics/{split}` | `getGroupStatistics` | `sort`, `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/groups/{group}/teams` | `getTeams` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/groups/{group}/teams/{team}/records/{split}` | `getTeamRecordBySplit` | `dates`, `month`, `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/groups/{group}/teams/{team}/statistics/{split}` | `getTeamSeasonStatsByTeamSeason` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/groups/{group}/teams/{team}/statistics/{split}/type/{stat}` | `getTeamSeasonStatsByTeamSeason` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/leaders` | `getLeadersByDate` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/leaders/{split}` | `getLeadersBySplitType` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/manufacturers/{manufacturer}/records/{split}` | `getManufacturerRecord` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/standings` | `getStandings` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/standings/{standingType}` | `getStandings` | `month`, `dates`, `live`, `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/statistics/{split}/byathlete` | `getPlayerSeasonStatsSeason` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/statistics/{split}/byteam` | `getPlayerSeasonStatsSeasonByTeam` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/summary` | `getLeagueSeasonSummary` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/teams/{team}/athletes/{athlete}/statistics` | `getPlayerSeasonStatsByPlayerTeamSeason` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/teams/{team}/athletes/{athlete}/statistics/{split}` | `getPlayerSeasonStatsByPlayerTeamSeason` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/teams/{team}/ats` | `getSpreadRecords` | `opp`, `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/teams/{team}/attendance` | `getTeamAttendance` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/teams/{team}/events` | `getTeamEventsBySeason` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/teams/{team}/leaders` | `getLeadersByTeamSeason` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/teams/{team}/leaders/{split}` | `getLeadersByTeamSeasonSplitType` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/teams/{team}/odds-records` | `getTeamOddsRecords` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/teams/{team}/record` | `getTeamRecord` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/teams/{team}/records` | `getTeamRecords` | `splits`, `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/teams/{team}/records/{split}` | `getTeamRecordBySplit` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/teams/{team}/statistics` | `getTeamSeasonStatsByTeamSeason` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/teams/{team}/statistics/{split}` | `getTeamSeasonStatsByTeamSeason` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/teams/{team}/statistics/{split}/byathlete` | `getPlayerSeasonStatsByTeam` | `stats`, `active`, `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/teams/{team}/statistics/{split}/type/{stat}` | `getTeamSeasonStatsByTeamSeason` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/teams/{team}/summary` | `getTeamSeasonSummary` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/weeks` | `getSeasonWeeks` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/weeks/{week}` | `getSeasonWeek` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/weeks/{week}/events` | `getSeasonWeekEvents` | `groups`, `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/weeks/{week}/players/{player}/ranks` | `getPlayerRankingsForWeek` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/weeks/{week}/players/{player}/ranks/{id}` | `getPlayerRankingForWeek` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/weeks/{week}/powerindex` | `getPowerIndexByWeek` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/weeks/{week}/qbr/{split}` | `getSeasonWeekQBR` | `qualified`, `sort`, `group`, `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/weeks/{week}/rankings` | `getRankingTypesForWeek` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/weeks/{week}/rankings/{id}` | `getRankingTypesForWeek` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/weeks/{week}/rankings/{id}/ranks` | `getRankingsForWeek` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/weeks/{week}/talentpicks` | `getPicks` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/weeks/{week}/teams/{team}/ranks` | `getTeamRankingsForWeek` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{season}/types/{type}/weeks/{week}/teams/{team}/ranks/{id}` | `getTeamRankingForWeek` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{sport}` | `getSport` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{sport}/coaches` | `getCoaches` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{sport}/coaches/{coach}` | `getCoaches` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{sport}/items` | `getShopForSport` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{sport}/venues` | `getVenues` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{sport}/venues/{id}` | `getVenue` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{sport}/weight-classes` | `getWeightClasses` | `gender`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{sport}/{league}/item/{id}` | `getTicket` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{sport}/{league}/items` | `getShop` | `teams`, `athletes`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{sport}/{league}/{event}` | `getTicketsForEvent` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{team}` | `getTeam` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{team}/awards` | `getAwardsByTeam` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{team}/calendar` | `getCalendars` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{team}/calendar/{calendarType}` | `getCalendar` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{team}/coaches` | `getCoachesByTeam` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{team}/events` | `getTeamEvents` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{team}/injuries` | `getInjuries` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{team}/injuries/{injuryId}` | `getInjury` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{team}/leaders` | `getTeamLeaders` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{team}/notes` | `getTeamNotes` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{team}/rank` | `getTeamRanking` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{team}/ranks` | `getTeamRankings` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{team}/recruitings` | `getRecruitingClasses` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{team}/recruits` | `getRecruitsByTeam` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{team}/seasons` | `getTeamSeasons` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{team}/series/vs-opponent/{opponentId}` | `getSeriesVsOpponent` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{team}/vsathlete/{athlete}` | `getPlayerVsTeamStats` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/{tournament}` | `getTournament` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{tournament}/seasons` | `getTournamentSeasons` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{tournament}/seasons/{season}` | `getTournamentSeason` | `eventType`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{tournament}/seasons/{season}/bracketology` | `getTournamentBracketology` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{tournament}/seasons/{season}/bracketology/{iteration}` | `getTournamentIterationBracketology` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/{tournament}/seasons/{season}/events/{event}` | `getTournamentSeasonByEventId` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2application.wadl` | `getWadl` | — |
| `https://sports.core.api.espn.com/v2{path}` | `getExternalGrammar` | — |

---

## V2 Sport-Scoped (Non-League) Endpoints

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/{sport}/athletes` | `getAthletes` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `sort`, `type`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/sports/{sport}/leagues` | `getLeagues` | `page`, `limit`, `profile`, `dates`, `active`, `classId`, `dates`, `sort`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/sports/{sport}/positions` | `getPositions` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/{sport}/teams` | `getTeams` | `page`, `limit`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses` |
| `https://sports.core.api.espn.com/v2/sports/{sport}/teams/{id}/events` | `getEventsByTeam` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId` |

---

## V3 Generic Endpoints

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v3/api-docs` | `getApiListings` | — |
| `https://sports.core.api.espn.com/v3/athletes` | `getAthletes` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/athletes/{athlete}` | `getAthlete` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/athletes/{athlete}/eventlog` | `getEventLog` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/athletes/{athlete}/plays` | `getAthletePlays` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/athletes/{athlete}/statisticslog` | `getAthleteStatisticsLog` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/broadcasts` | `getBroadcasts` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/calendar` | `getCalendar` | `type`, `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/coaches` | `getCoaches` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/coaches/{coach}` | `getCoach` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/colleges` | `getColleges` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/competitions/{competition}` | `getCompetition` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/draft` | `getDraft` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/draft/athletes` | `getDraftAthletes` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/draft/athletes/{athlete}` | `getDraftAthlete` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/events` | `getLeagueEvents` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/events/{eventGuid}` | `getEvent` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/events/{event}` | `getEvent` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/events/{event}/competitions/{competition}/competitors/{competitor}` | `getCompetitor` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/events/{event}/competitions/{competition}/drives` | `getDrives` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/events/{event}/competitions/{competition}/plays` | `getPlayByPlay` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/events/{event}/competitions/{competition}/plays/{play}` | `getPlay` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/export` | `getExportFile` | — |
| `https://sports.core.api.espn.com/v3/featured` | `getBetFeatured` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/freeagents` | `getFreeAgents` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/graphiql` | `graphiql` | `page`, `limit` |
| `https://sports.core.api.espn.com/v3/graphql` | `post` | `page`, `limit` |
| `https://sports.core.api.espn.com/v3/groups` | `getGroups` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/injuries` | `getInjuries` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/items` | `getShopItems` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/items/{id}` | `getShopItem` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/leagues` | `getLeagues` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/leagues/{leagueGuid}` | `getLeague` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/markets/{market}` | `getBetMarket` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/marquee-athletes/{product}` | `getMarqueeAthletes` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/media` | `getMedia` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/models/{model}` | `getToggles` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/odds` | `getOdds` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/powerindex` | `getPowerIndex` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/predictions` | `getPredictions` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/promotions` | `getBetPromotions` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/qbr` | `getQBR` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/rankings` | `getRankings` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/schema` | `generateSchema` | `page`, `limit` |
| `https://sports.core.api.espn.com/v3/series/{series}/events` | `getSeriesEvents` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports` | `getSports` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sportGuid}` | `getSport` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/standings` | `getLeagueStandings` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/statistics` | `getLeagueStatistics` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/talents` | `getTalents` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/talents/{talent}` | `getTalent` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/teams` | `getTeams` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/teams/{team}` | `getTeam` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/teams/{team}/calendar` | `getTeamCalendar` | `type`, `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/teams/{team}/depthcharts` | `getDepthCharts` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/teams/{team}/events` | `getTeamEvents` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/teams/{team}/plays` | `getTeamPlays` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/tournaments` | `getLeagueTournaments` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/tournaments/{tournament}` | `getLeagueTournament` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/transactions` | `getLeagueTransactions` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/trending` | `getBetTrending` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/types/{seasonType}/groups` | `getGroups` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/types/{seasonType}/groups/{group}` | `getGroup` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/types/{seasonType}/groups/{group}/events` | `getGroupEvents` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/types/{seasonType}/teams/{team}/events` | `getTeamSeasonTypeEvents` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/types/{seasonType}/weeks/{week}/events` | `getWeeksEvents` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/{api}` | `getApiDeclaration` | — |
| `https://sports.core.api.espn.com/v3/{athlete}` | `getAthlete` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/{athlete}/eventlog` | `getAthleteEventLog` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/{college}` | `getCollege` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/{sport}` | `getSport` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/{sport}/{league}/athletes/{athlete}` | `getAthleteImages` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/{sport}/{league}/teams/{team}` | `getTeamImages` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/{team}` | `getTeam` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3application.wadl` | `getWadl` | — |
| `https://sports.core.api.espn.com/v3{path}` | `getExternalGrammar` | — |
---

# FILE: `docs/sports/australian_football.md`

# 🏉 Australian Rules Football

> Australian rules football as tracked by the AFL (Australian Football League).

**Sport slug:** `australian-football`  
**Base URL (v2):** `https://sports.core.api.espn.com/v2/sports/australian-football/`  
**Base URL (v3):** `https://sports.core.api.espn.com/v3/sports/australian-football/`

---

## Leagues & Competitions

| Abbreviation | League Name | Slug | Full URL |
| --- | --- | --- | --- |
| `AFL` | AFL | `afl` | `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/afl` |

---

## API Endpoints

> All endpoints below follow the pattern:  
> `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}<sub-path>`  
> Replace `{league}` with a league slug from the table above.

### Common Query Parameters

Most list endpoints support: `page` (int), `limit` (int). Additional filters are documented per endpoint.

### Seasons & Calendar

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}/calendar` | `getCalendars` | `dates`, `page`, `limit`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}/seasons` | `getSeasons` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}/seasons/{season}/athletes` | `getAthletes` | `active`, `sort`, `page`, `limit`, `seasontypes`, `played`, `teamtypes`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}/seasons/{season}/draft` | `getDraftByYear` | `page`, `limit`, `available`, `position`, `team`, `sort`, `filter` |
| `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}/seasons/{season}/freeagents` | `getFreeAgents` | `page`, `limit`, `types`, `oldteams`, `newteams`, `position`, `sort` |
| `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}/seasons/{season}/manufacturers` | `getManufacturers` | `page`, `limit` |

### Teams

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}/teams` | `getTeams` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |

### Athletes / Players

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}/athletes` | `getAthletes` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |

### Events / Games

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}/events/{event}` | `getEvent` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}/events/{event}/competitions/{competition}` | `getCompetition` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}/events/{event}/competitions/{competition}/broadcasts` | `getBroadcasts` | `lang`, `region`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}/events/{event}/competitions/{competition}/competitors/{competitor}` | `getCompetitor` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}/events/{event}/competitions/{competition}/odds` | `getCompetitionOdds` | `provider.priority`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}/events/{event}/competitions/{competition}/officials` | `getOfficials` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}/events/{event}/competitions/{competition}/plays/{play}/personnel` | `getPersonnel` | `page`, `limit` |

### News & Media

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}/media` | `getMedia` | `page`, `limit` |

### Rankings & Awards

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}/rankings` | `getRankings` | `page`, `limit` |

### Venues

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}/venues` | `getVenues` | `page`, `limit` |

### Other

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}/casinos` | `getCasinos` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}/circuits` | `getCircuits` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}/countries` | `getCountries` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}/franchises` | `getFranchises` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}/positions` | `getPositions` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}/providers` | `getProviders` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}/recruiting` | `getRecruitingSeasons` | `page`, `limit`, `sort`, `position`, `status` |
| `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}/season` | `getCurrentSeason` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/australian-football/leagues/{league}/tournaments` | `getTournaments` | `majorsOnly`, `page`, `limit` |

---

## V3 Endpoints

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v3/sports/{sport}/athletes` | `getAthletes` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}` | `getLeague` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}/seasons/{season}` | `getSeason` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |

---

## Site API Endpoints

> These use `site.api.espn.com` and return user-friendly data (scores, rosters, news, etc.)

```
GET https://site.api.espn.com/apis/site/v2/sports/australian-football/{league}/{resource}
```

| Resource | Description |
|----------|-------------|
| `scoreboard` | Live scores & schedules |
| `scoreboard?dates={YYYYMMDD}` | Scores for a specific date |
| `teams` | All teams |
| `teams/{id}/roster` | Team roster |
| `standings` | Standings — returns stub `{"fullViewLink":{...}}` on `/apis/site/v2/`, use `/apis/v2/` instead |
| `news` | Latest news |

> ⚠️ **Standings Note:** The `/apis/site/v2/` path returns only a redirect stub for AFL standings. Use `/apis/v2/` instead:
> - `https://site.api.espn.com/apis/v2/sports/australian-football/afl/standings`
> - `https://site.web.api.espn.com/apis/v2/sports/australian-football/afl/standings`
> Both return full standings data including team stats, percentage, and form (verified 2026 season).

---

## Example API Calls

```bash
# AFL scoreboard (today)
curl "https://site.api.espn.com/apis/site/v2/sports/australian-football/afl/scoreboard"

# AFL standings — use /apis/v2/ (site/v2 returns only a stub redirect)
curl "https://site.api.espn.com/apis/v2/sports/australian-football/afl/standings"

# Alternative domain (identical response)
curl "https://site.web.api.espn.com/apis/v2/sports/australian-football/afl/standings"

# AFL teams
curl "https://site.api.espn.com/apis/site/v2/sports/australian-football/afl/teams"

# Get all Australian football leagues (core API)
curl "https://sports.core.api.espn.com/v2/sports/australian-football/leagues"

# AFL teams (core API)
curl "https://sports.core.api.espn.com/v2/sports/australian-football/leagues/afl/teams?limit=25"

# AFL events (core API)
curl "https://sports.core.api.espn.com/v2/sports/australian-football/leagues/afl/events"
```

---

# FILE: `docs/sports/baseball.md`

# ⚾ Baseball

> Baseball from Major League Baseball (MLB), college, winter leagues, and international tournaments.

**Sport slug:** `baseball`  
**Base URL (v2):** `https://sports.core.api.espn.com/v2/sports/baseball/`  
**Base URL (v3):** `https://sports.core.api.espn.com/v3/sports/baseball/`

---

## Leagues & Competitions

| Abbreviation | League Name | Slug | Full URL |
| --- | --- | --- | --- |
| `CBWS` | Caribbean Series | `caribbean-series` | `https://sports.core.api.espn.com/v2/sports/baseball/leagues/caribbean-series` |
| `CBASE` | NCAA Baseball | `college-baseball` | `https://sports.core.api.espn.com/v2/sports/baseball/leagues/college-baseball` |
| `CSOFT` | NCAA Softball | `college-softball` | `https://sports.core.api.espn.com/v2/sports/baseball/leagues/college-softball` |
| `DOMWL` | Dominican Winter League | `dominican-winter-league` | `https://sports.core.api.espn.com/v2/sports/baseball/leagues/dominican-winter-league` |
| `LITTLE LEAGUE BASEBALL WORLD SERIES` | Little League Baseball | `llb` | `https://sports.core.api.espn.com/v2/sports/baseball/leagues/llb` |
| `LITTLE LEAGUE SOFTBALL WORLD SERIES` | Little League Softball | `lls` | `https://sports.core.api.espn.com/v2/sports/baseball/leagues/lls` |
| `LMB` | Mexican League | `mexican-winter-league` | `https://sports.core.api.espn.com/v2/sports/baseball/leagues/mexican-winter-league` |
| `MLB` | Major League Baseball | `mlb` | `https://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb` |
| `OLYBB` | Olympics Men's Baseball | `olympics-baseball` | `https://sports.core.api.espn.com/v2/sports/baseball/leagues/olympics-baseball` |
| `PUERT` | Puerto Rican Winter League | `puerto-rican-winter-league` | `https://sports.core.api.espn.com/v2/sports/baseball/leagues/puerto-rican-winter-league` |
| `VENWL` | Venezuelan Winter League | `venezuelan-winter-league` | `https://sports.core.api.espn.com/v2/sports/baseball/leagues/venezuelan-winter-league` |
| `WBBC` | World Baseball Classic | `world-baseball-classic` | `https://sports.core.api.espn.com/v2/sports/baseball/leagues/world-baseball-classic` |

---

## API Endpoints

> All endpoints below follow the pattern:  
> `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}<sub-path>`  
> Replace `{league}` with a league slug from the table above.

### Common Query Parameters

Most list endpoints support: `page` (int), `limit` (int). Additional filters are documented per endpoint.

### Seasons & Calendar

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}/calendar` | `getCalendars` | `dates`, `page`, `limit`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}/seasons` | `getSeasons` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}/seasons/{season}/athletes` | `getAthletes` | `active`, `sort`, `page`, `limit`, `seasontypes`, `played`, `teamtypes`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}/seasons/{season}/draft` | `getDraftByYear` | `page`, `limit`, `available`, `position`, `team`, `sort`, `filter` |
| `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}/seasons/{season}/freeagents` | `getFreeAgents` | `page`, `limit`, `types`, `oldteams`, `newteams`, `position`, `sort` |
| `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}/seasons/{season}/manufacturers` | `getManufacturers` | `page`, `limit` |

### Teams

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}/teams` | `getTeams` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |

### Athletes / Players

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}/athletes` | `getAthletes` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |

### Events / Games

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}/events/{event}` | `getEvent` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}/events/{event}/competitions/{competition}` | `getCompetition` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}/events/{event}/competitions/{competition}/broadcasts` | `getBroadcasts` | `lang`, `region`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}/events/{event}/competitions/{competition}/competitors/{competitor}` | `getCompetitor` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}/events/{event}/competitions/{competition}/odds` | `getCompetitionOdds` | `provider.priority`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}/events/{event}/competitions/{competition}/officials` | `getOfficials` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}/events/{event}/competitions/{competition}/plays/{play}/personnel` | `getPersonnel` | `page`, `limit` |

### News & Media

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}/media` | `getMedia` | `page`, `limit` |

### Rankings & Awards

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}/rankings` | `getRankings` | `page`, `limit` |

### Venues

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}/venues` | `getVenues` | `page`, `limit` |

### Other

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}/casinos` | `getCasinos` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}/circuits` | `getCircuits` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}/countries` | `getCountries` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}/franchises` | `getFranchises` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}/positions` | `getPositions` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}/providers` | `getProviders` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}/recruiting` | `getRecruitingSeasons` | `page`, `limit`, `sort`, `position`, `status` |
| `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}/season` | `getCurrentSeason` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/baseball/leagues/{league}/tournaments` | `getTournaments` | `majorsOnly`, `page`, `limit` |

---

## V3 Endpoints

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v3/sports/{sport}/athletes` | `getAthletes` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}` | `getLeague` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}/seasons/{season}` | `getSeason` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |

---

## Site API Endpoints

> These use `site.api.espn.com` and return user-friendly data (scores, rosters, news, etc.)

```
GET https://site.api.espn.com/apis/site/v2/sports/baseball/{league}/{resource}
```

| Resource | Description |
|----------|-------------|
| `scoreboard` | Live scores & schedules |
| `scoreboard?dates={YYYYMMDD}` | Scores for a specific date |
| `teams` | All teams |
| `teams/{id}` | Single team |
| `teams/{id}/roster` | Team roster |
| `teams/{id}/schedule` | Team schedule |
| `teams/{id}/record` | Team record |
| `teams/{id}/news` | Team news |
| `teams/{id}/injuries` | Team injury report |
| `teams/{id}/leaders` | Team statistical leaders |
| `teams/{id}/depth-charts` | Depth charts |
| `injuries` | **League-wide** injury report (all teams) |
| `transactions` | Recent signings, trades, waivers |
| `statistics` | League statistical leaders |
| `groups` | Divisions |
| `standings` | ⚠️ Stub only — see note below |
| `news` | Latest news |
| `athletes/{id}/news` | Athlete-specific news |
| `summary?event={id}` | Full game summary + boxscore |

> ⚠️ **Standings Note:** The `/apis/site/v2/` path returns only a stub for standings. Use `/apis/v2/` instead:
> `https://site.api.espn.com/apis/v2/sports/baseball/{league}/standings`

---

## CDN Game Data

> Rich game packages via `cdn.espn.com`. Requires `?xhr=1`.

```bash
curl "https://cdn.espn.com/core/mlb/game?xhr=1&gameId={EVENT_ID}"
curl "https://cdn.espn.com/core/mlb/boxscore?xhr=1&gameId={EVENT_ID}"
curl "https://cdn.espn.com/core/mlb/scoreboard?xhr=1"
```

---

## Athlete Data (common/v3)

> Works for MLB: `stats`, `gamelog`, `overview`, `splits`. Also supports `statistics/byathlete` with category filtering.

```bash
curl "https://site.web.api.espn.com/apis/common/v3/sports/baseball/mlb/athletes/{id}/overview"
curl "https://site.web.api.espn.com/apis/common/v3/sports/baseball/mlb/athletes/{id}/stats"
curl "https://site.web.api.espn.com/apis/common/v3/sports/baseball/mlb/athletes/{id}/gamelog"
curl "https://site.web.api.espn.com/apis/common/v3/sports/baseball/mlb/athletes/{id}/splits"

# Stats leaderboard with category filter
curl "https://site.web.api.espn.com/apis/common/v3/sports/baseball/mlb/statistics/byathlete?category=batting&sort=batting.homeRuns:desc&season=2024&seasontype=2"
```

---

## Example API Calls

```bash
# MLB scoreboard (today)
curl "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"

# MLB scoreboard for a specific date
curl "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates=20250920"

# MLB standings (use /apis/v2/ — /apis/site/v2/ only returns a stub)
curl "https://site.api.espn.com/apis/v2/sports/baseball/mlb/standings"

# New York Yankees roster
curl "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/teams/10/roster"

# New York Yankees injuries
curl "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/teams/10/injuries"

# College Baseball scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/baseball/college-baseball/scoreboard"

# Get all baseball leagues (core API)
curl "https://sports.core.api.espn.com/v2/sports/baseball/leagues"

# MLB teams (core API)
curl "https://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb/teams?limit=50"

# MLB athletes (core API)
curl "https://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb/athletes?limit=100&active=true"

# World Baseball Classic teams
curl "https://sports.core.api.espn.com/v2/sports/baseball/leagues/world-baseball-classic/teams"
```

---

# FILE: `docs/sports/basketball.md`

# 🏀 Basketball

> Basketball from the NBA, WNBA, college, and international leagues (FIBA, NBL).

**Sport slug:** `basketball`  
**Base URL (v2):** `https://sports.core.api.espn.com/v2/sports/basketball/`  
**Base URL (v3):** `https://sports.core.api.espn.com/v3/sports/basketball/`

---

## Leagues & Competitions

| Abbreviation | League Name | Slug | Full URL |
| --- | --- | --- | --- |
| `FIBA` | FIBA World Cup | `fiba` | `https://sports.core.api.espn.com/v2/sports/basketball/leagues/fiba` |
| `NCAAM` | NCAA Men's Basketball | `mens-college-basketball` | `https://sports.core.api.espn.com/v2/sports/basketball/leagues/mens-college-basketball` |
| `OLYMPICS` | Olympics Men's Basketball | `mens-olympics-basketball` | `https://sports.core.api.espn.com/v2/sports/basketball/leagues/mens-olympics-basketball` |
| `NBA` | National Basketball Association | `nba` | `https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba` |
| `NBA G LEAGUE` | NBA G League | `nba-development` | `https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba-development` |
| `NBACC` | NBA California Classic Summer League | `nba-summer-california` | `https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba-summer-california` |
| `NBAGS` | Golden State Summer League | `nba-summer-golden-state` | `https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba-summer-golden-state` |
| `NBALV` | Las Vegas Summer League | `nba-summer-las-vegas` | `https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba-summer-las-vegas` |
| `NBAOR` | Orlando Summer League | `nba-summer-orlando` | `https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba-summer-orlando` |
| `NBAGS` | Sacramento Summer League | `nba-summer-sacramento` | `https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba-summer-sacramento` |
| `NBAUT` | Salt Lake City Summer League | `nba-summer-utah` | `https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba-summer-utah` |
| `NBL` | National Basketball League | `nbl` | `https://sports.core.api.espn.com/v2/sports/basketball/leagues/nbl` |
| `WNBA` | Women's National Basketball Association | `wnba` | `https://sports.core.api.espn.com/v2/sports/basketball/leagues/wnba` |
| `NCAAW` | NCAA Women's Basketball | `womens-college-basketball` | `https://sports.core.api.espn.com/v2/sports/basketball/leagues/womens-college-basketball` |
| `OLYMPICS` | Olympics Women's Basketball | `womens-olympics-basketball` | `https://sports.core.api.espn.com/v2/sports/basketball/leagues/womens-olympics-basketball` |

---

## API Endpoints

> All endpoints below follow the pattern:  
> `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}<sub-path>`  
> Replace `{league}` with a league slug from the table above.

### Common Query Parameters

Most list endpoints support: `page` (int), `limit` (int). Additional filters are documented per endpoint.

### Seasons & Calendar

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/calendar` | `getCalendars` | `dates`, `page`, `limit`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/seasons` | `getSeasons` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/seasons/{season}/athletes` | `getAthletes` | `active`, `sort`, `page`, `limit`, `seasontypes`, `played`, `teamtypes`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/seasons/{season}/draft` | `getDraftByYear` | `page`, `limit`, `available`, `position`, `team`, `sort`, `filter` |
| `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/seasons/{season}/freeagents` | `getFreeAgents` | `page`, `limit`, `types`, `oldteams`, `newteams`, `position`, `sort` |
| `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/seasons/{season}/manufacturers` | `getManufacturers` | `page`, `limit` |

### Teams

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/teams` | `getTeams` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |

### Athletes / Players

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/athletes` | `getAthletes` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |

### Events / Games

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/events/{event}` | `getEvent` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/events/{event}/competitions/{competition}` | `getCompetition` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/events/{event}/competitions/{competition}/broadcasts` | `getBroadcasts` | `lang`, `region`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/events/{event}/competitions/{competition}/competitors/{competitor}` | `getCompetitor` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/events/{event}/competitions/{competition}/odds` | `getCompetitionOdds` | `provider.priority`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/events/{event}/competitions/{competition}/officials` | `getOfficials` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/events/{event}/competitions/{competition}/plays/{play}/personnel` | `getPersonnel` | `page`, `limit` |

### News & Media

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/media` | `getMedia` | `page`, `limit` |

### Rankings & Awards

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/rankings` | `getRankings` | `page`, `limit` |

### Venues

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/venues` | `getVenues` | `page`, `limit` |

### Other

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/casinos` | `getCasinos` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/circuits` | `getCircuits` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/countries` | `getCountries` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/franchises` | `getFranchises` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/positions` | `getPositions` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/providers` | `getProviders` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/recruiting` | `getRecruitingSeasons` | `page`, `limit`, `sort`, `position`, `status` |
| `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/season` | `getCurrentSeason` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/basketball/leagues/{league}/tournaments` | `getTournaments` | `majorsOnly`, `page`, `limit` |

---

## V3 Endpoints

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v3/sports/{sport}/athletes` | `getAthletes` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}` | `getLeague` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}/seasons/{season}` | `getSeason` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |

---

## Site API Endpoints

> These use `site.api.espn.com` and return user-friendly data (scores, rosters, news, etc.)

```
GET https://site.api.espn.com/apis/site/v2/sports/basketball/{league}/{resource}
```

| Resource | Description |
|----------|-------------|
| `scoreboard` | Live scores & schedules |
| `scoreboard?dates={YYYYMMDD}` | Scores for a specific date |
| `teams` | All teams |
| `teams/{id}` | Single team |
| `teams/{id}/roster` | Team roster |
| `teams/{id}/schedule` | Team schedule |
| `teams/{id}/record` | Team record |
| `teams/{id}/news` | Team news |
| `teams/{id}/injuries` | Team injury report |
| `teams/{id}/leaders` | Team statistical leaders |
| `teams/{id}/depth-charts` | Depth charts |
| `injuries` | **League-wide** injury report (all teams) |
| `transactions` | Recent signings, trades, waivers |
| `statistics` | League statistical leaders |
| `groups` | Conferences and divisions |
| `draft` | Draft board (NBA only) |
| `standings` | ⚠️ Stub only — see note below |
| `news` | Latest news |
| `athletes/{id}/news` | Athlete-specific news |
| `summary?event={id}` | Full game summary + boxscore |
| `rankings` | Poll rankings (NCAA leagues only) |

> ⚠️ **Standings Note:** The `/apis/site/v2/` path returns only a stub for standings. Use `/apis/v2/` instead:
> `https://site.api.espn.com/apis/v2/sports/basketball/{league}/standings`

---

## CDN Game Data

> Rich game packages via `cdn.espn.com`. Requires `?xhr=1`. Returns a `gamepackageJSON` object containing drives, plays, win probability, scoring, and odds.

```bash
# Full game package
curl "https://cdn.espn.com/core/nba/game?xhr=1&gameId={EVENT_ID}"

# Specific views
curl "https://cdn.espn.com/core/nba/boxscore?xhr=1&gameId={EVENT_ID}"
curl "https://cdn.espn.com/core/nba/playbyplay?xhr=1&gameId={EVENT_ID}"
curl "https://cdn.espn.com/core/nba/matchup?xhr=1&gameId={EVENT_ID}"
curl "https://cdn.espn.com/core/nba/scoreboard?xhr=1"
```

---

## Athlete Data (common/v3)

> Individual player stats, game logs, splits, and overview via `site.web.api.espn.com`.

```bash
# Player overview (stats snapshot + next game + rotowire)
curl "https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{id}/overview"

# Season stats
curl "https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{id}/stats"

# Game log
curl "https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{id}/gamelog"

# Home/Away/Opponent splits
curl "https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{id}/splits"

# Stats leaderboard (all athletes ranked)
curl "https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/statistics/byathlete"
```

> ✅ Works for: NBA, WNBA, mens-college-basketball, womens-college-basketball

---

## Specialized Endpoints

### Bracketology (NCAA Tournament)

```bash
# Live bracket projections
GET https://sports.core.api.espn.com/v2/tournament/{tournamentId}/seasons/{year}/bracketology

# Bracket snapshot at a specific iteration
GET https://sports.core.api.espn.com/v2/tournament/{tournamentId}/seasons/{year}/bracketology/{iteration}
```

> Common tournament IDs: `22` = NCAA Men's, `23` = NCAA Women's

### Power Index (BPI)

```bash
# Season BPI ratings
GET https://sports.core.api.espn.com/v2/sports/basketball/leagues/mens-college-basketball/seasons/{year}/powerindex

# BPI leaders
GET https://sports.core.api.espn.com/v2/sports/basketball/leagues/mens-college-basketball/seasons/{year}/powerindex/leaders

# BPI by team
GET https://sports.core.api.espn.com/v2/sports/basketball/leagues/mens-college-basketball/seasons/{year}/powerindex/{teamId}
```

---

## Example API Calls

```bash
# NBA scoreboard (today)
curl "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"

# NBA scoreboard for a specific date
curl "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=20250320"

# NBA standings (use /apis/v2/ — /apis/site/v2/ only returns a stub)
curl "https://site.api.espn.com/apis/v2/sports/basketball/nba/standings"

# LA Lakers roster
curl "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/13/roster"

# LA Lakers injury report
curl "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/13/injuries"

# Men's College Basketball scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates=20250320-20250323"

# Get all basketball leagues (core API)
curl "https://sports.core.api.espn.com/v2/sports/basketball/leagues"

# NBA teams (core API)
curl "https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/teams?limit=50"

# NBA athletes (core API)
curl "https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/athletes?limit=100&active=true"

# NBA standings (core API)
curl "https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/standings"

# WNBA teams
curl "https://sports.core.api.espn.com/v2/sports/basketball/leagues/wnba/teams"

# FIBA World Cup teams
curl "https://sports.core.api.espn.com/v2/sports/basketball/leagues/fiba/teams"
```

---

# FILE: `docs/sports/college_sports.md`

# 🎓 College Sports

> ESPN API coverage of US college sports including Football (NCAAF), Men's & Women's Basketball (NCAAM/NCAAW), and Baseball.

---

## Supported College Leagues

| Sport | League Name | Slug | Core API URL |
|-------|------------|------|-------------|
| Football | NCAA Football | `college-football` | `sports.core.api.espn.com/v2/sports/football/leagues/college-football` |
| Men's Basketball | NCAA Men's Basketball | `mens-college-basketball` | `sports.core.api.espn.com/v2/sports/basketball/leagues/mens-college-basketball` |
| Women's Basketball | NCAA Women's Basketball | `womens-college-basketball` | `sports.core.api.espn.com/v2/sports/basketball/leagues/womens-college-basketball` |
| Baseball | NCAA Baseball | `college-baseball` | `sports.core.api.espn.com/v2/sports/baseball/leagues/college-baseball` |

---

## Site API Endpoints

```
GET https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/{resource}
```

| Resource | NCAAF | NCAAM | NCAAW | NCAAB |
|----------|-------|-------|-------|-------|
| `scoreboard` | ✅ | ✅ | ✅ | ✅ |
| `scoreboard?dates={YYYYMMDD}` | ✅ | ✅ | ✅ | ✅ |
| `teams` | ✅ | ✅ | ✅ | ✅ |
| `teams/{id}` | ✅ | ✅ | ✅ | ✅ |
| `teams/{id}/roster` | ✅ | ✅ | ✅ | ✅ |
| `teams/{id}/schedule` | ✅ | ✅ | ✅ | ✅ |
| `news` | ✅ | ✅ | ✅ | ✅ |
| `rankings` | ✅ | ✅ | — | — |
| `summary?event={id}` | ✅ | ✅ | ✅ | ✅ |
| `groups` | ✅ | ✅ | ✅ | ✅ |

---

## College Football Specifics

### Conference Filtering (groups)

```bash
# Filter scoreboard by conference group
curl "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?groups=80&dates=20241010"

# Common group IDs:
#   80 = FBS (all major conferences)
#   4  = ACC
#   8  = Big 12
#   9  = Pac-12
#  12  = SEC
#  21  = Big Ten
```

### Week-based Scoreboard

```bash
# NCAAF — Week 1, Regular Season
curl "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?week=1&seasontype=2"
```

### Rankings

```bash
# AP Top 25 + Coaches Poll
curl "https://site.api.espn.com/apis/site/v2/sports/football/college-football/rankings"
```

Response includes: `rankings[].name` (e.g. `"AP Top 25"`), `ranks[]` with team, current rank, previous rank, first place votes.

### Power Index (SP+)

```bash
curl "https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2024/powerindex"
curl "https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2024/powerindex/leaders"
```

### QBR

```bash
# College Football QBR (Group 80 = FBS)
curl "https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2024/types/2/groups/80/qbr/0"
```

### Recruiting

```bash
curl "https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2024/recruits"
```

---

## College Basketball Specifics

### Rankings

```bash
# AP Poll + USA Today Poll
curl "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/rankings"
```

### Power Index (BPI)

```bash
curl "https://sports.core.api.espn.com/v2/sports/basketball/leagues/mens-college-basketball/seasons/2025/powerindex"
curl "https://sports.core.api.espn.com/v2/sports/basketball/leagues/mens-college-basketball/seasons/2025/powerindex/leaders"
```

### NCAA Tournament Bracket

```bash
# Live bracket projections (Bracketology)
curl "https://sports.core.api.espn.com/v2/tournament/22/seasons/2025/bracketology"

# 22 = NCAA Men's Tournament, 23 = NCAA Women's Tournament
```

---

## CDN Game Data

```bash
# College Football — full game package
curl "https://cdn.espn.com/core/college-football/game?xhr=1&gameId={EVENT_ID}"
curl "https://cdn.espn.com/core/college-football/scoreboard?xhr=1"
```

---

## Example API Calls

```bash
# NCAAF scoreboard (all FBS games, current week)
curl "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?groups=80"

# NCAAF Week 1 scores
curl "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?week=1&seasontype=2&groups=80"

# Men's NCAAB scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"

# Women's NCAAB scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/basketball/womens-college-basketball/scoreboard"

# College Baseball scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/baseball/college-baseball/scoreboard"

# AP Top 25 in College Football
curl "https://site.api.espn.com/apis/site/v2/sports/football/college-football/rankings"

# AP Top 25 in NCAAB
curl "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/rankings"

# All NCAAF teams (use limit for pagination)
curl "https://site.api.espn.com/apis/site/v2/sports/football/college-football/teams?limit=500"

# All NCAAB teams
curl "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams?limit=500"
```

---

# FILE: `docs/sports/cricket.md`

# 🏏 Cricket

> Cricket leagues and tournaments.

**Sport slug:** `cricket`  
**Base URL (v2):** `https://sports.core.api.espn.com/v2/sports/cricket/`  
**Base URL (v3):** `https://sports.core.api.espn.com/v3/sports/cricket/`

---

## Leagues & Competitions

| Abbreviation | League Name | Slug | Full URL |
| --- | --- | --- | --- |

---

## API Endpoints

> All endpoints below follow the pattern:  
> `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}<sub-path>`  
> Replace `{league}` with a league slug from the table above.

### Common Query Parameters

Most list endpoints support: `page` (int), `limit` (int). Additional filters are documented per endpoint.

### Seasons & Calendar

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/calendar` | `getCalendars` | `dates`, `page`, `limit`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/seasons` | `getSeasons` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/seasons/{season}/athletes` | `getAthletes` | `active`, `sort`, `page`, `limit`, `seasontypes`, `played`, `teamtypes`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/seasons/{season}/draft` | `getDraftByYear` | `page`, `limit`, `available`, `position`, `team`, `sort`, `filter` |
| `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/seasons/{season}/freeagents` | `getFreeAgents` | `page`, `limit`, `types`, `oldteams`, `newteams`, `position`, `sort` |
| `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/seasons/{season}/manufacturers` | `getManufacturers` | `page`, `limit` |

### Teams

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/teams` | `getTeams` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |

### Athletes / Players

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/athletes` | `getAthletes` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |

### Events / Games

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/events/{event}` | `getEvent` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/events/{event}/competitions/{competition}` | `getCompetition` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/events/{event}/competitions/{competition}/broadcasts` | `getBroadcasts` | `lang`, `region`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/events/{event}/competitions/{competition}/competitors/{competitor}` | `getCompetitor` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/events/{event}/competitions/{competition}/odds` | `getCompetitionOdds` | `provider.priority`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/events/{event}/competitions/{competition}/officials` | `getOfficials` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/events/{event}/competitions/{competition}/plays/{play}/personnel` | `getPersonnel` | `page`, `limit` |

### News & Media

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/media` | `getMedia` | `page`, `limit` |

### Rankings & Awards

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/rankings` | `getRankings` | `page`, `limit` |

### Venues

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/venues` | `getVenues` | `page`, `limit` |

### Other

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/casinos` | `getCasinos` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/circuits` | `getCircuits` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/countries` | `getCountries` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/franchises` | `getFranchises` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/positions` | `getPositions` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/providers` | `getProviders` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/recruiting` | `getRecruitingSeasons` | `page`, `limit`, `sort`, `position`, `status` |
| `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/season` | `getCurrentSeason` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/tournaments` | `getTournaments` | `majorsOnly`, `page`, `limit` |

---

## V3 Endpoints

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v3/sports/{sport}/athletes` | `getAthletes` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}` | `getLeague` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}/seasons/{season}` | `getSeason` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |

---

## Site API Endpoints

> These use `site.api.espn.com` and return user-friendly data (scores, rosters, news, etc.)

```
GET https://site.api.espn.com/apis/site/v2/sports/cricket/{league}/{resource}
```

| Resource | Description |
|----------|-------------|
| `scoreboard` | ⚠️ Not available — see note below |
| `teams` | All teams |
| `standings` | Standings |
| `news` | Latest news |

> ⚠️ **Scoreboard Note:** The cricket scoreboard endpoint returns 404 on all tested domains and all league paths (`/cricket/8/`, `/cricket/icc/`, etc.) via the site API. To retrieve cricket events (matches), use the core API instead:
> ```
> https://sports.core.api.espn.com/v2/sports/cricket/leagues/{league}/events
> ```

---

## Example API Calls

```bash
# ICC T20 World Cup scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/cricket/icc.t20/scoreboard"

# IPL scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/cricket/ipl/scoreboard"

# Get all cricket leagues (core API)
curl "https://sports.core.api.espn.com/v2/sports/cricket/leagues"

# ICC T20 World Cup teams (core API)
curl "https://sports.core.api.espn.com/v2/sports/cricket/leagues/icc.t20/teams"

# ICC T20 World Cup events (core API)
curl "https://sports.core.api.espn.com/v2/sports/cricket/leagues/icc.t20/events"
```

---

# FILE: `docs/sports/field_hockey.md`

# 🏑 Field Hockey

> Women's college field hockey.

**Sport slug:** `field-hockey`  
**Base URL (v2):** `https://sports.core.api.espn.com/v2/sports/field-hockey/`  
**Base URL (v3):** `https://sports.core.api.espn.com/v3/sports/field-hockey/`

---

## Leagues & Competitions

| Abbreviation | League Name | Slug | Full URL |
| --- | --- | --- | --- |
| `CFHOC` | NCAA Women's Field Hockey | `womens-college-field-hockey` | `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/womens-college-field-hockey` |

---

## API Endpoints

> All endpoints below follow the pattern:  
> `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}<sub-path>`  
> Replace `{league}` with a league slug from the table above.

### Common Query Parameters

Most list endpoints support: `page` (int), `limit` (int). Additional filters are documented per endpoint.

### Seasons & Calendar

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}/calendar` | `getCalendars` | `dates`, `page`, `limit`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}/seasons` | `getSeasons` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}/seasons/{season}/athletes` | `getAthletes` | `active`, `sort`, `page`, `limit`, `seasontypes`, `played`, `teamtypes`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}/seasons/{season}/draft` | `getDraftByYear` | `page`, `limit`, `available`, `position`, `team`, `sort`, `filter` |
| `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}/seasons/{season}/freeagents` | `getFreeAgents` | `page`, `limit`, `types`, `oldteams`, `newteams`, `position`, `sort` |
| `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}/seasons/{season}/manufacturers` | `getManufacturers` | `page`, `limit` |

### Teams

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}/teams` | `getTeams` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |

### Athletes / Players

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}/athletes` | `getAthletes` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |

### Events / Games

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}/events/{event}` | `getEvent` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}/events/{event}/competitions/{competition}` | `getCompetition` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}/events/{event}/competitions/{competition}/broadcasts` | `getBroadcasts` | `lang`, `region`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}/events/{event}/competitions/{competition}/competitors/{competitor}` | `getCompetitor` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}/events/{event}/competitions/{competition}/odds` | `getCompetitionOdds` | `provider.priority`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}/events/{event}/competitions/{competition}/officials` | `getOfficials` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}/events/{event}/competitions/{competition}/plays/{play}/personnel` | `getPersonnel` | `page`, `limit` |

### News & Media

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}/media` | `getMedia` | `page`, `limit` |

### Rankings & Awards

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}/rankings` | `getRankings` | `page`, `limit` |

### Venues

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}/venues` | `getVenues` | `page`, `limit` |

### Other

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}/casinos` | `getCasinos` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}/circuits` | `getCircuits` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}/countries` | `getCountries` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}/franchises` | `getFranchises` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}/positions` | `getPositions` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}/providers` | `getProviders` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}/recruiting` | `getRecruitingSeasons` | `page`, `limit`, `sort`, `position`, `status` |
| `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}/season` | `getCurrentSeason` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/{league}/tournaments` | `getTournaments` | `majorsOnly`, `page`, `limit` |

---

## V3 Endpoints

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v3/sports/{sport}/athletes` | `getAthletes` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}` | `getLeague` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}/seasons/{season}` | `getSeason` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |

---

## Site API Endpoints

> These use `site.api.espn.com` and return user-friendly data (scores, rosters, news, etc.)

```
GET https://site.api.espn.com/apis/site/v2/sports/field-hockey/{league}/{resource}
```

| Resource | Description |
|----------|-------------|
| `scoreboard` | Live scores & schedules |
| `teams` | All teams |
| `standings` | Standings |
| `news` | Latest news |

---

## Example API Calls

```bash
# FIH Women scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/field-hockey/fih.w/scoreboard"

# FIH Men scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/field-hockey/fih.m/scoreboard"

# Get all field hockey leagues (core API)
curl "https://sports.core.api.espn.com/v2/sports/field-hockey/leagues"

# FIH Women events (core API)
curl "https://sports.core.api.espn.com/v2/sports/field-hockey/leagues/fih.w/events"
```

---

# FILE: `docs/sports/football.md`

# 🏈 Football

> American and Canadian football, including the NFL, CFL, College Football, UFL, and XFL.

**Sport slug:** `football`  
**Base URL (v2):** `https://sports.core.api.espn.com/v2/sports/football/`  
**Base URL (v3):** `https://sports.core.api.espn.com/v3/sports/football/`

---

## Leagues & Competitions

| Abbreviation | League Name | Slug | Full URL |
| --- | --- | --- | --- |
| `CFL` | Canadian Football League | `cfl` | `https://sports.core.api.espn.com/v2/sports/football/leagues/cfl` |
| `NCAAF` | NCAA - Football | `college-football` | `https://sports.core.api.espn.com/v2/sports/football/leagues/college-football` |
| `NFL` | National Football League | `nfl` | `https://sports.core.api.espn.com/v2/sports/football/leagues/nfl` |
| `UFL` | United Football League | `ufl` | `https://sports.core.api.espn.com/v2/sports/football/leagues/ufl` |
| `XFL` | XFL | `xfl` | `https://sports.core.api.espn.com/v2/sports/football/leagues/xfl` |

---

## API Endpoints

> All endpoints below follow the pattern:  
> `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}<sub-path>`  
> Replace `{league}` with a league slug from the table above.

### Common Query Parameters

Most list endpoints support: `page` (int), `limit` (int). Additional filters are documented per endpoint.

### Seasons & Calendar

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}/calendar` | `getCalendars` | `dates`, `page`, `limit`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}/seasons` | `getSeasons` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}/seasons/{season}/athletes` | `getAthletes` | `active`, `sort`, `page`, `limit`, `seasontypes`, `played`, `teamtypes`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}/seasons/{season}/draft` | `getDraftByYear` | `page`, `limit`, `available`, `position`, `team`, `sort`, `filter` |
| `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}/seasons/{season}/freeagents` | `getFreeAgents` | `page`, `limit`, `types`, `oldteams`, `newteams`, `position`, `sort` |
| `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}/seasons/{season}/manufacturers` | `getManufacturers` | `page`, `limit` |

### Teams

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}/teams` | `getTeams` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |

### Athletes / Players

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}/athletes` | `getAthletes` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |

### Events / Games

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}/events/{event}` | `getEvent` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}/events/{event}/competitions/{competition}` | `getCompetition` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}/events/{event}/competitions/{competition}/broadcasts` | `getBroadcasts` | `lang`, `region`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}/events/{event}/competitions/{competition}/competitors/{competitor}` | `getCompetitor` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}/events/{event}/competitions/{competition}/odds` | `getCompetitionOdds` | `provider.priority`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}/events/{event}/competitions/{competition}/officials` | `getOfficials` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}/events/{event}/competitions/{competition}/plays/{play}/personnel` | `getPersonnel` | `page`, `limit` |

### News & Media

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}/media` | `getMedia` | `page`, `limit` |

### Rankings & Awards

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}/rankings` | `getRankings` | `page`, `limit` |

### Venues

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}/venues` | `getVenues` | `page`, `limit` |

### Other

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}/casinos` | `getCasinos` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}/circuits` | `getCircuits` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}/countries` | `getCountries` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}/franchises` | `getFranchises` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}/positions` | `getPositions` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}/providers` | `getProviders` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}/recruiting` | `getRecruitingSeasons` | `page`, `limit`, `sort`, `position`, `status` |
| `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}/season` | `getCurrentSeason` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/football/leagues/{league}/tournaments` | `getTournaments` | `majorsOnly`, `page`, `limit` |

---

## V3 Endpoints

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v3/sports/{sport}/athletes` | `getAthletes` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}` | `getLeague` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}/seasons/{season}` | `getSeason` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |

---

## Site API Endpoints

> These use `site.api.espn.com` and return user-friendly data (scores, rosters, news, etc.)

```
GET https://site.api.espn.com/apis/site/v2/sports/football/{league}/{resource}
```

| Resource | Description |
|----------|-------------|
| `scoreboard` | Live scores & schedules |
| `scoreboard?week={n}&seasontype=2` | Scores for a specific week |
| `scoreboard?dates={YYYYMMDD}` | Scores for a specific date |
| `teams` | All teams |
| `teams/{id}` | Single team |
| `teams/{id}/roster` | Team roster |
| `teams/{id}/schedule` | Team schedule |
| `teams/{id}/record` | Team record |
| `teams/{id}/news` | Team news |
| `teams/{id}/depthcharts` | Depth charts |
| `teams/{id}/injuries` | Team injury report |
| `teams/{id}/leaders` | Team statistical leaders |
| `injuries` | **League-wide** injury report (all teams) |
| `transactions` | Recent signings, trades, waivers |
| `statistics` | League statistical leaders |
| `groups` | Conferences and divisions |
| `draft` | Draft board (NFL only) |
| `standings` | ⚠️ Stub only — see note below |
| `news` | Latest news |
| `athletes/{id}/news` | Athlete-specific news |
| `summary?event={id}` | Full game summary + boxscore |
| `rankings` | Poll rankings (college-football only) |

> ⚠️ **Standings Note:** The `/apis/site/v2/` path returns only a stub for standings. Use `/apis/v2/` instead:
> `https://site.api.espn.com/apis/v2/sports/football/{league}/standings`

---

## CDN Game Data

> Rich game packages via `cdn.espn.com`. Requires `?xhr=1`. Contains drives, play-by-play, win probability, scoring, and odds inside `gamepackageJSON`.

```bash
# NFL — full game package
curl "https://cdn.espn.com/core/nfl/game?xhr=1&gameId={EVENT_ID}"

# College football
curl "https://cdn.espn.com/core/college-football/game?xhr=1&gameId={EVENT_ID}"

# Specific views (nfl or college-football)
curl "https://cdn.espn.com/core/nfl/boxscore?xhr=1&gameId={EVENT_ID}"
curl "https://cdn.espn.com/core/nfl/playbyplay?xhr=1&gameId={EVENT_ID}"
curl "https://cdn.espn.com/core/nfl/matchup?xhr=1&gameId={EVENT_ID}"
curl "https://cdn.espn.com/core/nfl/scoreboard?xhr=1"
```

---

## Athlete Data (common/v3)

> Individual player stats, game logs, and splits via `site.web.api.espn.com`. Works for NFL; also applies to college-football.

```bash
# Player overview (stats + next game + rotowire notes)
curl "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/{id}/overview"

# Season stats
curl "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/{id}/stats"

# Game log
curl "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/{id}/gamelog"

# Home/Away/Opponent splits
curl "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/{id}/splits"

# Stats leaderboard (all athletes ranked)
curl "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/statistics/byathlete"
```

---

## Specialized Endpoints

### QBR (Total Quarterback Rating)

```bash
# Season totals QBR (NFL)
GET https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/{year}/types/2/groups/1/qbr/0

# Weekly QBR (NFL)
GET https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/{year}/types/2/weeks/{week}/qbr/0

# College Football QBR (NCAAF)
GET https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/{year}/types/2/groups/80/qbr/0
```

> **Split values:** `0` = totals, `1` = home, `2` = away

### Recruiting

```bash
# Top recruiting class by year (NCAAF)
GET https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/{year}/recruits

# Recruiting class by team
GET https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/{year}/classes/{teamId}
```

### Power Index (SP+)

```bash
# Season SP+ ratings
GET https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/{year}/powerindex

# SP+ leaders
GET https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/{year}/powerindex/leaders
```

---

## Example API Calls

```bash
# NFL scoreboard (all games this week)
curl "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

# NFL Week 1 scores
curl "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?week=1&seasontype=2"

# NFL standings (use /apis/v2/ — /apis/site/v2/ only returns a stub)
curl "https://site.api.espn.com/apis/v2/sports/football/nfl/standings"

# Dallas Cowboys roster
curl "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/6/roster"

# Dallas Cowboys depth chart
curl "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/6/depthcharts"

# Dallas Cowboys injury report
curl "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/6/injuries"

# College Football scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?week=1&seasontype=2&groups=80"

# Get all NFL leagues
curl "https://sports.core.api.espn.com/v2/sports/football/leagues"

# NFL teams (core API)
curl "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/teams?limit=50"

# NFL current season events
curl "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events"

# NFL athletes (core API)
curl "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/athletes?limit=100&active=true"

# NFL standings (core API)
curl "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/standings"

# CFL teams
curl "https://sports.core.api.espn.com/v2/sports/football/leagues/cfl/teams"
```

---

# FILE: `docs/sports/golf.md`

# ⛳ Golf

> Professional golf tours including PGA TOUR, LPGA, DP World Tour (European Tour), LIV Golf, and more.

**Sport slug:** `golf`  
**Base URL (v2):** `https://sports.core.api.espn.com/v2/sports/golf/`  
**Base URL (v3):** `https://sports.core.api.espn.com/v3/sports/golf/`

---

## Leagues & Competitions

| Abbreviation | League Name | Slug | Full URL |
| --- | --- | --- | --- |
| `SGA` | PGA TOUR Champions | `champions-tour` | `https://sports.core.api.espn.com/v2/sports/golf/leagues/champions-tour` |
| `EUR` | DP World Tour | `eur` | `https://sports.core.api.espn.com/v2/sports/golf/leagues/eur` |
| `LIV` | LIV Golf Invitational Series | `liv` | `https://sports.core.api.espn.com/v2/sports/golf/leagues/liv` |
| `LPGA` | Ladies Pro Golf Association | `lpga` | `https://sports.core.api.espn.com/v2/sports/golf/leagues/lpga` |
| `OLYM` | Olympic Golf - Men | `mens-olympics-golf` | `https://sports.core.api.espn.com/v2/sports/golf/leagues/mens-olympics-golf` |
| `KORN FERRY` | Korn Ferry Tour | `ntw` | `https://sports.core.api.espn.com/v2/sports/golf/leagues/ntw` |
| `PGA` | PGA TOUR | `pga` | `https://sports.core.api.espn.com/v2/sports/golf/leagues/pga` |
| `TGL` | TGL | `tgl` | `https://sports.core.api.espn.com/v2/sports/golf/leagues/tgl` |
| `OLYW` | Olympic Golf - Women | `womens-olympics-golf` | `https://sports.core.api.espn.com/v2/sports/golf/leagues/womens-olympics-golf` |

---

## API Endpoints

> All endpoints below follow the pattern:  
> `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}<sub-path>`  
> Replace `{league}` with a league slug from the table above.

### Common Query Parameters

Most list endpoints support: `page` (int), `limit` (int). Additional filters are documented per endpoint.

### Seasons & Calendar

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}/calendar` | `getCalendars` | `dates`, `page`, `limit`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}/seasons` | `getSeasons` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}/seasons/{season}/athletes` | `getAthletes` | `active`, `sort`, `page`, `limit`, `seasontypes`, `played`, `teamtypes`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}/seasons/{season}/draft` | `getDraftByYear` | `page`, `limit`, `available`, `position`, `team`, `sort`, `filter` |
| `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}/seasons/{season}/freeagents` | `getFreeAgents` | `page`, `limit`, `types`, `oldteams`, `newteams`, `position`, `sort` |
| `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}/seasons/{season}/manufacturers` | `getManufacturers` | `page`, `limit` |

### Teams

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}/teams` | `getTeams` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |

### Athletes / Players

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}/athletes` | `getAthletes` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |

### Events / Games

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}/events/{event}` | `getEvent` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}/events/{event}/competitions/{competition}` | `getCompetition` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}/events/{event}/competitions/{competition}/broadcasts` | `getBroadcasts` | `lang`, `region`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}/events/{event}/competitions/{competition}/competitors/{competitor}` | `getCompetitor` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}/events/{event}/competitions/{competition}/odds` | `getCompetitionOdds` | `provider.priority`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}/events/{event}/competitions/{competition}/officials` | `getOfficials` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}/events/{event}/competitions/{competition}/plays/{play}/personnel` | `getPersonnel` | `page`, `limit` |

### News & Media

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}/media` | `getMedia` | `page`, `limit` |

### Rankings & Awards

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}/rankings` | `getRankings` | `page`, `limit` |

### Venues

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}/venues` | `getVenues` | `page`, `limit` |

### Other

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}/casinos` | `getCasinos` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}/circuits` | `getCircuits` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}/countries` | `getCountries` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}/franchises` | `getFranchises` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}/positions` | `getPositions` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}/providers` | `getProviders` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}/recruiting` | `getRecruitingSeasons` | `page`, `limit`, `sort`, `position`, `status` |
| `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}/season` | `getCurrentSeason` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/golf/leagues/{league}/tournaments` | `getTournaments` | `majorsOnly`, `page`, `limit` |

---

## V3 Endpoints

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v3/sports/{sport}/athletes` | `getAthletes` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}` | `getLeague` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}/seasons/{season}` | `getSeason` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |

---

## Site API Endpoints

> These use `site.api.espn.com` and return user-friendly data (scores, rosters, news, etc.)

```
GET https://site.api.espn.com/apis/site/v2/sports/golf/{league}/{resource}
```

| Resource | Description |
|----------|-------------|
| `scoreboard` | Live tournament scores |
| `scoreboard?dates={YYYYMMDD}` | Scores for a specific date range |
| `leaderboard?tournamentId={id}` | Tournament leaderboard |
| `news` | Latest news |
| `athletes/{id}/news` | Player-specific news |
| `summary?event={id}` | Tournament summary + results |

> ⚠️ **Slug required:** Golf scoreboard requires a named league slug — numeric IDs return 400.
> Use: `pga`, `lpga`, `liv`, `eur` (European Tour)

> ⚠️ **Injuries endpoint returns 500** for Golf — not supported.

---

## Example API Calls

```bash
# PGA TOUR scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard"

# LPGA scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/golf/lpga/scoreboard"

# LIV Golf scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/golf/liv/scoreboard"

# Get all golf leagues (core API)
curl "https://sports.core.api.espn.com/v2/sports/golf/leagues"

# PGA TOUR athletes (core API)
curl "https://sports.core.api.espn.com/v2/sports/golf/leagues/pga/athletes?limit=100&active=true"

# PGA TOUR events (core API)
curl "https://sports.core.api.espn.com/v2/sports/golf/leagues/pga/events"
```

---

# FILE: `docs/sports/hockey.md`

# 🏒 Ice Hockey

> Ice hockey from the NHL, college, and international play.

**Sport slug:** `hockey`  
**Base URL (v2):** `https://sports.core.api.espn.com/v2/sports/hockey/`  
**Base URL (v3):** `https://sports.core.api.espn.com/v3/sports/hockey/`

---

## Leagues & Competitions

| Abbreviation | League Name | Slug | Full URL |
| --- | --- | --- | --- |
| `WCH` | World Cup of Hockey | `hockey-world-cup` | `https://sports.core.api.espn.com/v2/sports/hockey/leagues/hockey-world-cup` |
| `NCAAH` | NCAA Men's Ice Hockey | `mens-college-hockey` | `https://sports.core.api.espn.com/v2/sports/hockey/leagues/mens-college-hockey` |
| `NHL` | National Hockey League | `nhl` | `https://sports.core.api.espn.com/v2/sports/hockey/leagues/nhl` |
| `MEN'S ICE HOCKEY` | Men's Ice Hockey | `olympics-mens-ice-hockey` | `https://sports.core.api.espn.com/v2/sports/hockey/leagues/olympics-mens-ice-hockey` |
| `WOMEN'S ICE HOCKEY` | Women's Ice Hockey | `olympics-womens-ice-hockey` | `https://sports.core.api.espn.com/v2/sports/hockey/leagues/olympics-womens-ice-hockey` |
| `CWHOC` | NCAA Women's Hockey | `womens-college-hockey` | `https://sports.core.api.espn.com/v2/sports/hockey/leagues/womens-college-hockey` |

---

## API Endpoints

> All endpoints below follow the pattern:  
> `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}<sub-path>`  
> Replace `{league}` with a league slug from the table above.

### Common Query Parameters

Most list endpoints support: `page` (int), `limit` (int). Additional filters are documented per endpoint.

### Seasons & Calendar

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}/calendar` | `getCalendars` | `dates`, `page`, `limit`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}/seasons` | `getSeasons` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}/seasons/{season}/athletes` | `getAthletes` | `active`, `sort`, `page`, `limit`, `seasontypes`, `played`, `teamtypes`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}/seasons/{season}/draft` | `getDraftByYear` | `page`, `limit`, `available`, `position`, `team`, `sort`, `filter` |
| `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}/seasons/{season}/freeagents` | `getFreeAgents` | `page`, `limit`, `types`, `oldteams`, `newteams`, `position`, `sort` |
| `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}/seasons/{season}/manufacturers` | `getManufacturers` | `page`, `limit` |

### Teams

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}/teams` | `getTeams` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |

### Athletes / Players

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}/athletes` | `getAthletes` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |

### Events / Games

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}/events/{event}` | `getEvent` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}/events/{event}/competitions/{competition}` | `getCompetition` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}/events/{event}/competitions/{competition}/broadcasts` | `getBroadcasts` | `lang`, `region`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}/events/{event}/competitions/{competition}/competitors/{competitor}` | `getCompetitor` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}/events/{event}/competitions/{competition}/odds` | `getCompetitionOdds` | `provider.priority`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}/events/{event}/competitions/{competition}/officials` | `getOfficials` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}/events/{event}/competitions/{competition}/plays/{play}/personnel` | `getPersonnel` | `page`, `limit` |

### News & Media

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}/media` | `getMedia` | `page`, `limit` |

### Rankings & Awards

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}/rankings` | `getRankings` | `page`, `limit` |

### Venues

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}/venues` | `getVenues` | `page`, `limit` |

### Other

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}/casinos` | `getCasinos` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}/circuits` | `getCircuits` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}/countries` | `getCountries` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}/franchises` | `getFranchises` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}/positions` | `getPositions` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}/providers` | `getProviders` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}/recruiting` | `getRecruitingSeasons` | `page`, `limit`, `sort`, `position`, `status` |
| `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}/season` | `getCurrentSeason` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/hockey/leagues/{league}/tournaments` | `getTournaments` | `majorsOnly`, `page`, `limit` |

---

## V3 Endpoints

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v3/sports/{sport}/athletes` | `getAthletes` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}` | `getLeague` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}/seasons/{season}` | `getSeason` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |

---

## Site API Endpoints

> These use `site.api.espn.com` and return user-friendly data (scores, rosters, news, etc.)

```
GET https://site.api.espn.com/apis/site/v2/sports/hockey/{league}/{resource}
```

| Resource | Description |
|----------|-------------|
| `scoreboard` | Live scores & schedules |
| `scoreboard?dates={YYYYMMDD}` | Scores for a specific date |
| `teams` | All teams |
| `teams/{id}` | Single team |
| `teams/{id}/roster` | Team roster |
| `teams/{id}/schedule` | Team schedule |
| `teams/{id}/record` | Team record |
| `teams/{id}/news` | Team news |
| `teams/{id}/injuries` | Team injury report |
| `teams/{id}/leaders` | Team statistical leaders |
| `teams/{id}/depth-charts` | Depth charts |
| `injuries` | **League-wide** injury report (all teams) |
| `transactions` | Recent signings, trades, waivers |
| `statistics` | League statistical leaders |
| `groups` | Conferences and divisions |
| `standings` | ⚠️ Stub only — see note below |
| `news` | Latest news |
| `athletes/{id}/news` | Athlete-specific news |
| `summary?event={id}` | Full game summary + boxscore |

> ⚠️ **Standings Note:** The `/apis/site/v2/` path returns only a stub for standings. Use `/apis/v2/` instead:
> `https://site.api.espn.com/apis/v2/sports/hockey/{league}/standings`

---

## CDN Game Data

> Rich game packages via `cdn.espn.com`. Requires `?xhr=1`.

```bash
curl "https://cdn.espn.com/core/nhl/game?xhr=1&gameId={EVENT_ID}"
curl "https://cdn.espn.com/core/nhl/boxscore?xhr=1&gameId={EVENT_ID}"
curl "https://cdn.espn.com/core/nhl/scoreboard?xhr=1"
```

---

## Athlete Data (common/v3)

> Works for NHL: `stats`, `overview`, `splits`. Note: `gamelog` returns 404 for NHL.

```bash
curl "https://site.web.api.espn.com/apis/common/v3/sports/hockey/nhl/athletes/{id}/overview"
curl "https://site.web.api.espn.com/apis/common/v3/sports/hockey/nhl/athletes/{id}/stats"
curl "https://site.web.api.espn.com/apis/common/v3/sports/hockey/nhl/athletes/{id}/splits"
curl "https://site.web.api.espn.com/apis/common/v3/sports/hockey/nhl/statistics/byathlete"
```

---

## Example API Calls

```bash
# NHL scoreboard (today)
curl "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard"

# NHL scoreboard for a specific date
curl "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard?dates=20250415"

# NHL standings (use /apis/v2/ — /apis/site/v2/ only returns a stub)
curl "https://site.api.espn.com/apis/v2/sports/hockey/nhl/standings"

# Toronto Maple Leafs roster
curl "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/teams/28/roster"

# Toronto Maple Leafs injuries
curl "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/teams/28/injuries"

# College Hockey Men scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/hockey/mens-college-hockey/scoreboard"

# Get all hockey leagues (core API)
curl "https://sports.core.api.espn.com/v2/sports/hockey/leagues"

# NHL teams (core API)
curl "https://sports.core.api.espn.com/v2/sports/hockey/leagues/nhl/teams?limit=50"

# NHL athletes (core API)
curl "https://sports.core.api.espn.com/v2/sports/hockey/leagues/nhl/athletes?limit=100&active=true"

# NHL standings (core API)
curl "https://sports.core.api.espn.com/v2/sports/hockey/leagues/nhl/standings"
```

---

# FILE: `docs/sports/lacrosse.md`

# 🥍 Lacrosse

> Lacrosse from the NLL, PLL, and NCAA.

**Sport slug:** `lacrosse`  
**Base URL (v2):** `https://sports.core.api.espn.com/v2/sports/lacrosse/`  
**Base URL (v3):** `https://sports.core.api.espn.com/v3/sports/lacrosse/`

---

## Leagues & Competitions

| Abbreviation | League Name | Slug | Full URL |
| --- | --- | --- | --- |
| `NCAAM LACROSSE` | NCAA Men's Lacrosse | `mens-college-lacrosse` | `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/mens-college-lacrosse` |
| `NLL` | National Lacrosse League | `nll` | `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/nll` |
| `PLL` | Premier Lacrosse League | `pll` | `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/pll` |
| `NCAAW LACROSSE` | NCAA Women's Lacrosse | `womens-college-lacrosse` | `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/womens-college-lacrosse` |

---

## API Endpoints

> All endpoints below follow the pattern:  
> `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}<sub-path>`  
> Replace `{league}` with a league slug from the table above.

### Common Query Parameters

Most list endpoints support: `page` (int), `limit` (int). Additional filters are documented per endpoint.

### Seasons & Calendar

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}/calendar` | `getCalendars` | `dates`, `page`, `limit`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}/seasons` | `getSeasons` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}/seasons/{season}/athletes` | `getAthletes` | `active`, `sort`, `page`, `limit`, `seasontypes`, `played`, `teamtypes`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}/seasons/{season}/draft` | `getDraftByYear` | `page`, `limit`, `available`, `position`, `team`, `sort`, `filter` |
| `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}/seasons/{season}/freeagents` | `getFreeAgents` | `page`, `limit`, `types`, `oldteams`, `newteams`, `position`, `sort` |
| `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}/seasons/{season}/manufacturers` | `getManufacturers` | `page`, `limit` |

### Teams

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}/teams` | `getTeams` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |

### Athletes / Players

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}/athletes` | `getAthletes` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |

### Events / Games

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}/events/{event}` | `getEvent` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}/events/{event}/competitions/{competition}` | `getCompetition` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}/events/{event}/competitions/{competition}/broadcasts` | `getBroadcasts` | `lang`, `region`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}/events/{event}/competitions/{competition}/competitors/{competitor}` | `getCompetitor` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}/events/{event}/competitions/{competition}/odds` | `getCompetitionOdds` | `provider.priority`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}/events/{event}/competitions/{competition}/officials` | `getOfficials` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}/events/{event}/competitions/{competition}/plays/{play}/personnel` | `getPersonnel` | `page`, `limit` |

### News & Media

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}/media` | `getMedia` | `page`, `limit` |

### Rankings & Awards

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}/rankings` | `getRankings` | `page`, `limit` |

### Venues

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}/venues` | `getVenues` | `page`, `limit` |

### Other

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}/casinos` | `getCasinos` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}/circuits` | `getCircuits` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}/countries` | `getCountries` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}/franchises` | `getFranchises` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}/positions` | `getPositions` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}/providers` | `getProviders` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}/recruiting` | `getRecruitingSeasons` | `page`, `limit`, `sort`, `position`, `status` |
| `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}/season` | `getCurrentSeason` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/{league}/tournaments` | `getTournaments` | `majorsOnly`, `page`, `limit` |

---

## V3 Endpoints

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v3/sports/{sport}/athletes` | `getAthletes` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}` | `getLeague` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}/seasons/{season}` | `getSeason` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |

---

## Site API Endpoints

> These use `site.api.espn.com` and return user-friendly data (scores, rosters, news, etc.)

```
GET https://site.api.espn.com/apis/site/v2/sports/lacrosse/{league}/{resource}
```

| Resource | Description |
|----------|-------------|
| `scoreboard` | Live scores & schedules |
| `teams` | All teams |
| `standings` | League standings |
| `news` | Latest news |

---

## Example API Calls

```bash
# PLL scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/lacrosse/pll/scoreboard"

# NLL scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/lacrosse/nll/scoreboard"

# Get all lacrosse leagues (core API)
curl "https://sports.core.api.espn.com/v2/sports/lacrosse/leagues"

# PLL teams (core API)
curl "https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/pll/teams"

# PLL events (core API)
curl "https://sports.core.api.espn.com/v2/sports/lacrosse/leagues/pll/events"
```

---

# FILE: `docs/sports/mma.md`

# 🥊 MMA

> Mixed Martial Arts from the UFC, Bellator, and dozens of international promotions.

**Sport slug:** `mma`  
**Base URL (v2):** `https://sports.core.api.espn.com/v2/sports/mma/`  
**Base URL (v3):** `https://sports.core.api.espn.com/v3/sports/mma/`

---

## Leagues & Competitions

> ESPN tracks **50+ MMA organizations**. Key slugs listed below. Use `https://sports.core.api.espn.com/v2/sports/mma/leagues` for the full list.

### Major Promotions

| Abbreviation | League Name | Slug | Full URL |
| --- | --- | --- | --- |
| `UFC` | Ultimate Fighting Championship | `ufc` | `https://sports.core.api.espn.com/v2/sports/mma/leagues/ufc` |
| `BEL` | Bellator MMA | `bellator` | `https://sports.core.api.espn.com/v2/sports/mma/leagues/bellator` |
| `IFC` | Invicta FC (Women's) | `ifc` | `https://sports.core.api.espn.com/v2/sports/mma/leagues/ifc` |
| `LFA` | Legacy Fighting Alliance | `lfa` | `https://sports.core.api.espn.com/v2/sports/mma/leagues/lfa` |
| `KSW` | Konfrontacja Sztuk Walki | `ksw` | `https://sports.core.api.espn.com/v2/sports/mma/leagues/ksw` |
| `CW` | Cage Warriors | `cage-warriors` | `https://sports.core.api.espn.com/v2/sports/mma/leagues/cage-warriors` |
| `ACB` | Absolute Championship Berkut | `absolute` | `https://sports.core.api.espn.com/v2/sports/mma/leagues/absolute` |
| `FNG` | Fight Nights Global | `fng` | `https://sports.core.api.espn.com/v2/sports/mma/leagues/fng` |
| `K1` | K-1 | `k1` | `https://sports.core.api.espn.com/v2/sports/mma/leagues/k1` |
| `M1` | M-1 Mix-Fight Championship | `m1` | `https://sports.core.api.espn.com/v2/sports/mma/leagues/m1` |
| `IFL` | International Fight League | `ifl` | `https://sports.core.api.espn.com/v2/sports/mma/leagues/ifl` |
| `DRM` | Dream | `dream` | `https://sports.core.api.espn.com/v2/sports/mma/leagues/dream` |

### Additional International Promotions (partial)

| Slug | Name |
|------|------|
| `affliction` | Affliction |
| `bang-fighting` | Bang Fighting Championships |
| `banzay` | Banzay Fight Championship |
| `battlezone` | Battlezone Fighting Championships |
| `blackout` | Blackout Fighting Championship |
| `bosnia` | Bosnia Fight Championship |
| `boxe` | Boxe Fight Combat |
| `brazilian-freestyle` | Brazilian Freestyle Circuit |
| `budo` | Budo Fighting Championships |
| `lfc` | Legacy Fighting Championship |

---

## API Endpoints

> All endpoints below follow the pattern:  

### Seasons & Calendar

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/mma/leagues/{league}/calendar` | `getCalendars` | `dates`, `page`, `limit`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/mma/leagues/{league}/seasons` | `getSeasons` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/mma/leagues/{league}/seasons/{season}/athletes` | `getAthletes` | `active`, `sort`, `page`, `limit`, `seasontypes`, `played`, `teamtypes`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/sports/mma/leagues/{league}/seasons/{season}/draft` | `getDraftByYear` | `page`, `limit`, `available`, `position`, `team`, `sort`, `filter` |
| `https://sports.core.api.espn.com/v2/sports/mma/leagues/{league}/seasons/{season}/freeagents` | `getFreeAgents` | `page`, `limit`, `types`, `oldteams`, `newteams`, `position`, `sort` |
| `https://sports.core.api.espn.com/v2/sports/mma/leagues/{league}/seasons/{season}/manufacturers` | `getManufacturers` | `page`, `limit` |

### Teams

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/mma/leagues/{league}/teams` | `getTeams` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |

### Athletes / Players

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/mma/leagues/{league}/athletes` | `getAthletes` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |

### Events / Games

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/mma/leagues/{league}/events/{event}` | `getEvent` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/mma/leagues/{league}/events/{event}/competitions/{competition}` | `getCompetition` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/sports/mma/leagues/{league}/events/{event}/competitions/{competition}/broadcasts` | `getBroadcasts` | `lang`, `region`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/mma/leagues/{league}/events/{event}/competitions/{competition}/competitors/{competitor}` | `getCompetitor` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/sports/mma/leagues/{league}/events/{event}/competitions/{competition}/odds` | `getCompetitionOdds` | `provider.priority`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/mma/leagues/{league}/events/{event}/competitions/{competition}/officials` | `getOfficials` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/mma/leagues/{league}/events/{event}/competitions/{competition}/plays/{play}/personnel` | `getPersonnel` | `page`, `limit` |

### News & Media

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/mma/leagues/{league}/media` | `getMedia` | `page`, `limit` |

### Rankings & Awards

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/mma/leagues/{league}/rankings` | `getRankings` | `page`, `limit` |

### Venues

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/mma/leagues/{league}/venues` | `getVenues` | `page`, `limit` |

### Other

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/mma/leagues/{league}/casinos` | `getCasinos` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/mma/leagues/{league}/circuits` | `getCircuits` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/mma/leagues/{league}/countries` | `getCountries` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/mma/leagues/{league}/franchises` | `getFranchises` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/mma/leagues/{league}/positions` | `getPositions` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/mma/leagues/{league}/providers` | `getProviders` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/mma/leagues/{league}/recruiting` | `getRecruitingSeasons` | `page`, `limit`, `sort`, `position`, `status` |
| `https://sports.core.api.espn.com/v2/sports/mma/leagues/{league}/season` | `getCurrentSeason` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/mma/leagues/{league}/tournaments` | `getTournaments` | `majorsOnly`, `page`, `limit` |

---

## V3 Endpoints

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v3/sports/{sport}/athletes` | `getAthletes` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}` | `getLeague` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}/seasons/{season}` | `getSeason` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |

---

## Site API Endpoints

> These use `site.api.espn.com` and return user-friendly data (scores, rosters, news, etc.)

```
GET https://site.api.espn.com/apis/site/v2/sports/mma/{league}/{resource}
```

| Resource | Description |
|----------|-------------|
| `scoreboard` | Event results & schedules |
| `scoreboard?dates={YYYYMMDD}` | Events for a specific date |
| `teams` | Fighter teams/stables (if available) |
| `news` | Latest news |
| `athletes/{id}/news` | Fighter-specific news |
| `summary?event={id}` | Event summary + fight results |

> ⚠️ **Injuries endpoint returns 500** for MMA — not supported.  
> ⚠️ **Standings not applicable** for MMA — use event/athlete endpoints.  
> ✅ For fighter profiles and fight history, use the Core API:  
> `sports.core.api.espn.com/v2/sports/mma/leagues/ufc/athletes/{id}`

---

## Example API Calls

```bash
# UFC scoreboard (events)
curl "https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard"

# Get all MMA leagues (core API)
curl "https://sports.core.api.espn.com/v2/sports/mma/leagues"

# UFC athletes (core API)
curl "https://sports.core.api.espn.com/v2/sports/mma/leagues/ufc/athletes?limit=100&active=true"

# UFC events (core API)
curl "https://sports.core.api.espn.com/v2/sports/mma/leagues/ufc/events"
```

---

# FILE: `docs/sports/racing.md`

# 🏎️ Motor Sports

> Motorsport including Formula 1, IndyCar, and NASCAR.

**Sport slug:** `racing`  
**Base URL (v2):** `https://sports.core.api.espn.com/v2/sports/racing/`  
**Base URL (v3):** `https://sports.core.api.espn.com/v3/sports/racing/`

---

## Leagues & Competitions

| Abbreviation | League Name | Slug | Full URL |
| --- | --- | --- | --- |
| `F1` | Formula 1 | `f1` | `https://sports.core.api.espn.com/v2/sports/racing/leagues/f1` |
| `IRL` | IndyCar Series | `irl` | `https://sports.core.api.espn.com/v2/sports/racing/leagues/irl` |
| `NASCAR-PREMIER` | NASCAR Cup Series | `nascar-premier` | `https://sports.core.api.espn.com/v2/sports/racing/leagues/nascar-premier` |
| `NASCAR-SECONDARY` | NASCAR O'Reilly Auto Parts Series | `nascar-secondary` | `https://sports.core.api.espn.com/v2/sports/racing/leagues/nascar-secondary` |
| `NASCAR-TRUCK` | NASCAR Truck Series | `nascar-truck` | `https://sports.core.api.espn.com/v2/sports/racing/leagues/nascar-truck` |

---

## API Endpoints

> All endpoints below follow the pattern:  
> `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}<sub-path>`  
> Replace `{league}` with a league slug from the table above.

### Common Query Parameters

Most list endpoints support: `page` (int), `limit` (int). Additional filters are documented per endpoint.

### Seasons & Calendar

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/calendar` | `getCalendars` | `dates`, `page`, `limit`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/seasons` | `getSeasons` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/seasons/{season}/athletes` | `getAthletes` | `active`, `sort`, `page`, `limit`, `seasontypes`, `played`, `teamtypes`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/seasons/{season}/draft` | `getDraftByYear` | `page`, `limit`, `available`, `position`, `team`, `sort`, `filter` |
| `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/seasons/{season}/freeagents` | `getFreeAgents` | `page`, `limit`, `types`, `oldteams`, `newteams`, `position`, `sort` |
| `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/seasons/{season}/manufacturers` | `getManufacturers` | `page`, `limit` |

### Teams

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/teams` | `getTeams` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |

### Athletes / Players

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/athletes` | `getAthletes` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |

### Events / Games

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/events/{event}` | `getEvent` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/events/{event}/competitions/{competition}` | `getCompetition` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/events/{event}/competitions/{competition}/broadcasts` | `getBroadcasts` | `lang`, `region`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/events/{event}/competitions/{competition}/competitors/{competitor}` | `getCompetitor` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/events/{event}/competitions/{competition}/odds` | `getCompetitionOdds` | `provider.priority`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/events/{event}/competitions/{competition}/officials` | `getOfficials` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/events/{event}/competitions/{competition}/plays/{play}/personnel` | `getPersonnel` | `page`, `limit` |

### News & Media

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/media` | `getMedia` | `page`, `limit` |

### Rankings & Awards

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/rankings` | `getRankings` | `page`, `limit` |

### Venues

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/venues` | `getVenues` | `page`, `limit` |

### Other

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/casinos` | `getCasinos` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/circuits` | `getCircuits` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/countries` | `getCountries` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/franchises` | `getFranchises` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/positions` | `getPositions` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/providers` | `getProviders` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/recruiting` | `getRecruitingSeasons` | `page`, `limit`, `sort`, `position`, `status` |
| `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/season` | `getCurrentSeason` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/tournaments` | `getTournaments` | `majorsOnly`, `page`, `limit` |

---

## V3 Endpoints

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v3/sports/{sport}/athletes` | `getAthletes` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}` | `getLeague` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}/seasons/{season}` | `getSeason` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |

---

## Site API Endpoints

> These use `site.api.espn.com` and return user-friendly data (scores, rosters, news, etc.)

```
GET https://site.api.espn.com/apis/site/v2/sports/racing/{league}/{resource}
```

| Resource | Description |
|----------|-------------|
| `scoreboard` | Race results & schedules |
| `news` | Latest news |

---

## Example API Calls

```bash
# Formula 1 scoreboard (race results)
curl "https://site.api.espn.com/apis/site/v2/sports/racing/f1/scoreboard"

# IndyCar scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/racing/irl/scoreboard"

# NASCAR Cup scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/racing/nascar-premier/scoreboard"

# Get all racing leagues (core API)
curl "https://sports.core.api.espn.com/v2/sports/racing/leagues"

# F1 athletes (core API)
curl "https://sports.core.api.espn.com/v2/sports/racing/leagues/f1/athletes?limit=50"

# F1 events (core API)
curl "https://sports.core.api.espn.com/v2/sports/racing/leagues/f1/events"
```

---

# FILE: `docs/sports/rugby.md`

# 🏉 Rugby

> Rugby Union encompassing international test matches, Six Nations, World Cup, Premiership, Top 14, and more.

> `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}<sub-path>`  
> Replace `{league}` with a league slug from the table above.

### Common Query Parameters

Most list endpoints support: `page` (int), `limit` (int). Additional filters are documented per endpoint.

### Seasons & Calendar

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/calendar` | `getCalendars` | `dates`, `page`, `limit`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/seasons` | `getSeasons` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/seasons/{season}/athletes` | `getAthletes` | `active`, `sort`, `page`, `limit`, `seasontypes`, `played`, `teamtypes`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/seasons/{season}/draft` | `getDraftByYear` | `page`, `limit`, `available`, `position`, `team`, `sort`, `filter` |
| `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/seasons/{season}/freeagents` | `getFreeAgents` | `page`, `limit`, `types`, `oldteams`, `newteams`, `position`, `sort` |
| `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/seasons/{season}/manufacturers` | `getManufacturers` | `page`, `limit` |

### Teams

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/teams` | `getTeams` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |

### Athletes / Players

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/athletes` | `getAthletes` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |

### Events / Games

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/events/{event}` | `getEvent` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/events/{event}/competitions/{competition}` | `getCompetition` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/events/{event}/competitions/{competition}/broadcasts` | `getBroadcasts` | `lang`, `region`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/events/{event}/competitions/{competition}/competitors/{competitor}` | `getCompetitor` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/events/{event}/competitions/{competition}/odds` | `getCompetitionOdds` | `provider.priority`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/events/{event}/competitions/{competition}/officials` | `getOfficials` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/events/{event}/competitions/{competition}/plays/{play}/personnel` | `getPersonnel` | `page`, `limit` |

### News & Media

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/media` | `getMedia` | `page`, `limit` |

### Rankings & Awards

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/rankings` | `getRankings` | `page`, `limit` |

### Venues

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/venues` | `getVenues` | `page`, `limit` |

### Other

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/casinos` | `getCasinos` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/circuits` | `getCircuits` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/countries` | `getCountries` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/franchises` | `getFranchises` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/positions` | `getPositions` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/providers` | `getProviders` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/recruiting` | `getRecruitingSeasons` | `page`, `limit`, `sort`, `position`, `status` |
| `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/season` | `getCurrentSeason` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/tournaments` | `getTournaments` | `majorsOnly`, `page`, `limit` |

---

## V3 Endpoints

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v3/sports/{sport}/athletes` | `getAthletes` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}` | `getLeague` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}/seasons/{season}` | `getSeason` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |

---

## Site API Endpoints

> These use `site.api.espn.com` and return user-friendly data (scores, rosters, news, etc.)

```
GET https://site.api.espn.com/apis/site/v2/sports/rugby/{league}/{resource}
```

| Resource | Description |
|----------|-------------|
| `scoreboard` | Live scores & schedules |
| `scoreboard?dates={YYYYMMDD}` | Scores for a specific date |
| `teams` | All teams |
| `teams/{id}` | Single team |
| `teams/{id}/roster` | Team roster |
| `teams/{id}/schedule` | Team schedule |
| `news` | Latest news |
| `summary?event={id}` | Full game summary + boxscore |
| `standings` | ⚠️ Broken — see note below |

> ⚠️ **Standings Note:** Rugby Union standings have **very limited API support**:
> - `/apis/site/v2/` returns a **500 error** for all tested league IDs
> - `/apis/v2/` (both `site.api` and `site.web.api`) returns **empty `{"children":[], "seasons":{}}`**
> 
> Standings data is **not reliably available** for Rugby Union via the site API (tested with league IDs 267 and 180).
> Use `sports.core.api.espn.com/v2/sports/rugby/leagues/{league}/standings` for reference data instead.

---

## Example API Calls

> **Remember:** Rugby uses numeric league IDs — not named slugs.

```bash
# Get all rugby leagues (discover available IDs)
curl "https://sports.core.api.espn.com/v2/sports/rugby/leagues"

# Rugby World Cup scoreboard (site API uses numeric ID)
curl "https://site.api.espn.com/apis/site/v2/sports/rugby/164205/scoreboard"

# Six Nations scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/rugby/180659/scoreboard"

# Gallagher Premiership scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/rugby/267979/scoreboard"

# Super Rugby Pacific scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/rugby/242041/scoreboard"

# Rugby World Cup teams (core API)
curl "https://sports.core.api.espn.com/v2/sports/rugby/leagues/164205/teams"

# Six Nations standings — NOTE: /apis/v2/ returns empty {} for rugby union
# Use the core API reference endpoint instead:
curl "https://sports.core.api.espn.com/v2/sports/rugby/leagues/267/standings"

# Rugby World Cup events (core API)
curl "https://sports.core.api.espn.com/v2/sports/rugby/leagues/164205/events"

# Major League Rugby scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/rugby/289262/scoreboard"
```

---

# FILE: `docs/sports/rugby_league.md`

# 🏉 Rugby League

> Rugby League encompassing NRL, Super League, State of Origin, and international competitions.

**Sport slug:** `rugby-league`  
**Base URL (v2):** `https://sports.core.api.espn.com/v2/sports/rugby-league/`  
**Base URL (v3):** `https://sports.core.api.espn.com/v3/sports/rugby-league/`

---

## Leagues & Competitions

> **⚠️ Rugby League uses numeric IDs as league slugs.** All competitions are served under a single parent slug: `3`. Use `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues` to discover available IDs.

| League Name | Numeric ID (slug) | Full URL |
| --- | --- | --- |
| Rugby League (NRL, Super League, State of Origin, etc.) | `3` | `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/3` |

---

## API Endpoints

> All endpoints below follow the pattern:  

### Seasons & Calendar

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/{league}/calendar` | `getCalendars` | `dates`, `page`, `limit`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/{league}/seasons` | `getSeasons` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/{league}/seasons/{season}/athletes` | `getAthletes` | `active`, `sort`, `page`, `limit`, `seasontypes`, `played`, `teamtypes`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/{league}/seasons/{season}/draft` | `getDraftByYear` | `page`, `limit`, `available`, `position`, `team`, `sort`, `filter` |
| `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/{league}/seasons/{season}/freeagents` | `getFreeAgents` | `page`, `limit`, `types`, `oldteams`, `newteams`, `position`, `sort` |
| `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/{league}/seasons/{season}/manufacturers` | `getManufacturers` | `page`, `limit` |

### Teams

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/{league}/teams` | `getTeams` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |

### Athletes / Players

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/{league}/athletes` | `getAthletes` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |

### Events / Games

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/{league}/events/{event}` | `getEvent` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/{league}/events/{event}/competitions/{competition}` | `getCompetition` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/{league}/events/{event}/competitions/{competition}/broadcasts` | `getBroadcasts` | `lang`, `region`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/{league}/events/{event}/competitions/{competition}/competitors/{competitor}` | `getCompetitor` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/{league}/events/{event}/competitions/{competition}/odds` | `getCompetitionOdds` | `provider.priority`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/{league}/events/{event}/competitions/{competition}/officials` | `getOfficials` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/{league}/events/{event}/competitions/{competition}/plays/{play}/personnel` | `getPersonnel` | `page`, `limit` |

### News & Media

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/{league}/media` | `getMedia` | `page`, `limit` |

### Rankings & Awards

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/{league}/rankings` | `getRankings` | `page`, `limit` |

### Venues

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/{league}/venues` | `getVenues` | `page`, `limit` |

### Other

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/{league}/casinos` | `getCasinos` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/{league}/circuits` | `getCircuits` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/{league}/countries` | `getCountries` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/{league}/franchises` | `getFranchises` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/{league}/positions` | `getPositions` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/{league}/providers` | `getProviders` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/{league}/recruiting` | `getRecruitingSeasons` | `page`, `limit`, `sort`, `position`, `status` |
| `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/{league}/season` | `getCurrentSeason` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/{league}/tournaments` | `getTournaments` | `majorsOnly`, `page`, `limit` |

---

## V3 Endpoints

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v3/sports/{sport}/athletes` | `getAthletes` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}` | `getLeague` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}/seasons/{season}` | `getSeason` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |

---

## Site API Endpoints

> These use `site.api.espn.com` and return user-friendly data (scores, rosters, news, etc.)

```
GET https://site.api.espn.com/apis/site/v2/sports/rugby-league/{league}/{resource}
```

| Resource | Description |
|----------|-------------|
| `scoreboard` | Live scores & schedules |
| `scoreboard?dates={YYYYMMDD}` | Scores for a specific date |
| `teams` | All teams |
| `teams/{id}` | Single team |
| `teams/{id}/roster` | Team roster |
| `teams/{id}/schedule` | Team schedule |
| `teams/{id}/news` | Team news |
| `injuries` | League-wide injury report |
| `news` | Latest news |
| `summary?event={id}` | Full game summary + boxscore |
| `standings` | ⚠️ Stub only — see note below |

> ⚠️ **Standings Note:** The `/apis/site/v2/` path returns only a stub for standings. Use `/apis/v2/` instead:
> `https://site.api.espn.com/apis/v2/sports/rugby-league/{league}/standings`

> ⚠️ **League ID Note:** Rugby League uses numeric league ID `3` — not named slugs like `nrl`.

---

## Example API Calls

> **Remember:** Rugby League uses numeric league ID `3` — not named slugs like `nrl`.

```bash
# Get all rugby league competitions (returns full structure under ID 3)
curl "https://sports.core.api.espn.com/v2/sports/rugby-league/leagues"

# NRL / Super League scoreboard (all rugby league under ID 3)
curl "https://site.api.espn.com/apis/site/v2/sports/rugby-league/3/scoreboard"

# Standings (use /apis/v2/ — /apis/site/v2/ only returns a stub)
curl "https://site.api.espn.com/apis/v2/sports/rugby-league/3/standings"

# Teams (core API)
curl "https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/3/teams"

# Events (core API)
curl "https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/3/events"

# Athletes
curl "https://sports.core.api.espn.com/v2/sports/rugby-league/leagues/3/athletes?limit=50&active=true"
```

---

# FILE: `docs/sports/soccer.md`

#  Soccer

> Association football  Premier League, La Liga, Bundesliga, Serie A, Ligue 1, MLS, UCL, and international tournaments.

**Sport slug:** `soccer`
**Base URL (v2):** `https://sports.core.api.espn.com/v2/sports/soccer/`
**Base URL (v3):** `https://sports.core.api.espn.com/v3/sports/soccer/`

---

## Leagues & Competitions

> This expanded list was compiled from the ESPN API and community contributions. See [issue #7](https://github.com/pseudo-r/Public-ESPN-API/issues/7).

###  International / FIFA

| Slug | Description |
| --- | --- |
| `fifa.world` | FIFA World Cup |
| `fifa.wwc` | FIFA Women's World Cup |
| `fifa.world.u20` | FIFA Under-20 World Cup |
| `fifa.world.u17` | FIFA Under-17 World Cup |
| `fifa.wworld.u17` | FIFA Under-17 Women's World Cup |
| `fifa.cwc` | FIFA Club World Cup |
| `fifa.friendly` | International Friendly |
| `fifa.friendly.w` | Women's International Friendly |
| `fifa.friendly_u21` | Under-21 International Friendly |
| `fifa.u20.friendly` | International U20 Friendly |
| `fifa.shebelieves` | SheBelieves Cup |
| `fifa.w.champions_cup` | FIFA Women's Champions Cup |
| `fifa.intercontinental_cup` | FIFA Intercontinental Cup |
| `fifa.olympics` | Men's Olympic Soccer Tournament |
| `fifa.w.olympics` | Women's Olympic Soccer Tournament |
| `fifa.worldq` | World Cup Qualifying |
| `fifa.worldq.uefa` | FIFA World Cup Qualifying - UEFA |
| `fifa.worldq.caf` | FIFA World Cup Qualifying - CAF |
| `fifa.worldq.afc` | FIFA World Cup Qualifying - AFC |
| `fifa.worldq.concacaf` | FIFA World Cup Qualifying - Concacaf |
| `fifa.worldq.conmebol` | FIFA World Cup Qualifying - CONMEBOL |
| `fifa.worldq.ofc` | FIFA World Cup Qualifying - OFC |
| `fifa.wwcq.ply` | FIFA Women's World Cup Qualifying - Playoff |
| `fifa.wworldq.uefa` | FIFA Women's World Cup Qualifying - UEFA |

###  UEFA

| Slug | Description |
| --- | --- |
| `uefa.champions` | UEFA Champions League |
| `uefa.champions_qual` | UEFA Champions League Qualifying |
| `uefa.europa` | UEFA Europa League |
| `uefa.europa_qual` | UEFA Europa League Qualifying |
| `uefa.europa.conf` | UEFA Conference League |
| `uefa.europa.conf_qual` | UEFA Conference League Qualifying |
| `uefa.super_cup` | UEFA Super Cup |
| `uefa.wchampions` | UEFA Women's Champions League |
| `uefa.euro` | UEFA European Championship |
| `uefa.euroq` | UEFA European Championship Qualifying |
| `uefa.weuro` | UEFA Women's European Championship |
| `uefa.euro_u21` | UEFA European Under-21 Championship |
| `uefa.euro_u21_qual` | UEFA European Under-21 Championship Qualifying |
| `uefa.euro.u19` | UEFA European Under-19 Championship |
| `uefa.nations` | UEFA Nations League |
| `uefa.w.nations` | UEFA Women's Nations League |

###  England

| Slug | Description |
| --- | --- |
| `eng.1` | English Premier League |
| `eng.2` | English Championship |
| `eng.3` | English League One |
| `eng.4` | English League Two |
| `eng.5` | English National League |
| `eng.fa` | English FA Cup |
| `eng.league_cup` | English Carabao Cup |
| `eng.trophy` | English EFL Trophy |
| `eng.charity` | English FA Community Shield |
| `eng.asia_trophy` | Premier League Asia Trophy |
| `eng.w.1` | English Women's Super League |
| `eng.w.fa` | English Women's FA Cup |
| `eng.w.charity` | English Women's FA Community Shield |

###  Spain

| Slug | Description |
| --- | --- |
| `esp.1` | Spanish LALIGA |
| `esp.2` | Spanish LALIGA 2 |
| `esp.copa_del_rey` | Spanish Copa del Rey |
| `esp.super_cup` | Spanish Supercopa |
| `esp.joan_gamper` | Trofeo Joan Gamper |
| `esp.w.1` | Spanish Liga F |
| `esp.copa_de_la_reina` | Spanish Copa de la Reina |

###  Germany

| Slug | Description |
| --- | --- |
| `ger.1` | German Bundesliga |
| `ger.2` | German 2. Bundesliga |
| `ger.dfb_pokal` | German Cup |
| `ger.super_cup` | German Supercup |
| `ger.playoff.relegation` | German Bundesliga Promotion/Relegation Playoff |
| `ger.2.promotion.relegation` | German Bundesliga 2 Promotion/Relegation Playoffs |

###  Italy

| Slug | Description |
| --- | --- |
| `ita.1` | Italian Serie A |
| `ita.2` | Italian Serie B |
| `ita.coppa_italia` | Coppa Italia |
| `ita.super_cup` | Italian Supercoppa |

###  France

| Slug | Description |
| --- | --- |
| `fra.1` | French Ligue 1 |
| `fra.2` | French Ligue 2 |
| `fra.coupe_de_france` | Coupe de France |
| `fra.super_cup` | French Trophee des Champions |
| `fra.w.1` | French Premiere Ligue |

###  Netherlands

| Slug | Description |
| --- | --- |
| `ned.1` | Dutch Eredivisie |
| `ned.2` | Dutch Keuken Kampioen Divisie |
| `ned.3` | Dutch Tweede Divisie |
| `ned.cup` | Dutch KNVB Beker |
| `ned.supercup` | Dutch Johan Cruyff Shield |
| `ned.w.1` | Dutch Vrouwen Eredivisie |
| `ned.w.knvb_cup` | Dutch KNVB Beker Vrouwen |

###  Scotland

| Slug | Description |
| --- | --- |
| `sco.1` | Scottish Premiership |
| `sco.2` | Scottish Championship |
| `sco.3` | Scottish League One |
| `sco.4` | Scottish League Two |
| `sco.tennents` | Scottish Cup |
| `sco.cis` | Scottish League Cup |
| `sco.challenge` | Scottish League Challenge Cup |

###  Portugal /  Belgium /  Austria / Other Europe

| Slug | Description |
| --- | --- |
| `por.1` | Portuguese Primeira Liga |
| `por.taca.portugal` | Taca de Portugal |
| `bel.1` | Belgian Pro League |
| `aut.1` | Austrian Bundesliga |
| `gre.1` | Greek Super League |
| `tur.1` | Turkish Super Lig |
| `den.1` | Danish Superliga |
| `nor.1` | Norwegian Eliteserien |
| `swe.1` | Swedish Allsvenskan |
| `cyp.1` | Cypriot First Division |
| `irl.1` | Irish Premier Division |
| `rus.1` | Russian Premier League |

###  USA / CONCACAF

| Slug | Description |
| --- | --- |
| `usa.1` | MLS |
| `usa.open` | U.S. Open Cup |
| `usa.nwsl` | NWSL |
| `usa.nwsl.cup` | NWSL Challenge Cup |
| `usa.nwsl.summer.cup` | NWSL X Liga MX Femenil Summer Cup |
| `usa.usl.1` | USL Championship |
| `usa.usl.l1` | USL League One |
| `usa.w.usl.1` | USL Super League |
| `usa.ncaa.m.1` | NCAA Men's Soccer |
| `usa.ncaa.w.1` | NCAA Women's Soccer |
| `concacaf.champions` | Concacaf Champions Cup |
| `concacaf.leagues.cup` | Leagues Cup |
| `concacaf.gold` | Concacaf Gold Cup |
| `concacaf.nations.league` | Concacaf Nations League |
| `concacaf.w.gold` | Concacaf W Gold Cup |
| `concacaf.w.champions_cup` | Concacaf W Champions Cup |
| `campeones.cup` | Campeones Cup |
| `can.w.nsl` | Northern Super League (Canada) |

###  Mexico

| Slug | Description |
| --- | --- |
| `mex.1` | Mexican Liga BBVA MX |
| `mex.2` | Mexican Liga de Expansion MX |
| `mex.campeon` | Mexican Campeon de Campeones |
| `mex.supercopa` | Mexican Supercopa MX |

###  South America / CONMEBOL

| Slug | Description |
| --- | --- |
| `conmebol.libertadores` | CONMEBOL Libertadores |
| `conmebol.sudamericana` | CONMEBOL Sudamericana |
| `conmebol.recopa` | CONMEBOL Recopa |
| `conmebol.america` | Copa America |
| `conmebol.america_qual` | Copa America Qualifying |
| `conmebol.america.femenina` | Copa America Femenina |
| `global.finalissima` | CONMEBOL-UEFA Cup of Champions |
| `arg.1` | Argentine Liga Profesional de Futbol |
| `arg.copa` | Copa Argentina |
| `bra.1` | Brazilian Serie A |
| `bra.2` | Brazilian Serie B |
| `bra.copa_do_brazil` | Copa do Brasil |
| `chi.1` | Chilean Primera Division |
| `col.1` | Colombian Primera A |
| `par.1` | Paraguayan Primera Division |
| `per.1` | Peruvian Liga 1 |
| `uru.1` | Liga AUF Uruguaya |
| `bol.1` | Bolivian Liga Profesional |
| `ecu.1` | LigaPro Ecuador |
| `ven.1` | Venezuelan Primera Division |

###  Africa / CAF

| Slug | Description |
| --- | --- |
| `caf.nations` | Africa Cup of Nations |
| `caf.nations_qual` | Africa Cup of Nations Qualifying |
| `caf.champions` | CAF Champions League |
| `caf.confed` | CAF Confederation Cup |
| `rsa.1` | South African Premiership |
| `nga.1` | Nigerian Professional League |
| `gha.1` | Ghanaian Premier League |

###  Asia / Middle East / Oceania

| Slug | Description |
| --- | --- |
| `afc.champions` | AFC Champions League Elite |
| `afc.cup` | AFC Champions League Two |
| `afc.asian.cup` | AFC Asian Cup |
| `ksa.1` | Saudi Pro League |
| `ksa.kings.cup` | Saudi King's Cup |
| `jpn.1` | Japanese J.League |
| `chn.1` | Chinese Super League |
| `ind.1` | Indian Super League |
| `tha.1` | Thai League 1 |
| `mys.1` | Malaysian Super League |
| `idn.1` | Indonesian Super League |
| `sgp.1` | Singaporean Premier League |
| `aus.1` | Australian A-League Men |
| `aus.w.1` | Australian A-League Women |

###  Club Friendlies & Misc

| Slug | Description |
| --- | --- |
| `club.friendly` | Club Friendly |
| `nonfifa` | Non-FIFA Friendly |
| `friendly.emirates_cup` | Emirates Cup |
| `global.champs_cup` | International Champions Cup |
| `generic.ussf` | Misc. U.S. Soccer Games |

---

## API Endpoints

> All endpoints follow the pattern:
> `https://sports.core.api.espn.com/v2/sports/soccer/leagues/{league}<sub-path>`
> Replace `{league}` with a slug from the tables above.

### Common Query Parameters

Most list endpoints support: `page` (int), `limit` (int).

### Seasons & Calendar

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/soccer/leagues/{league}/calendar` | `getCalendars` | `dates`, `page`, `limit`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/soccer/leagues/{league}/seasons` | `getSeasons` | `page`, `limit`, `utcOffset`, `dates`, `groups`, `profile`, `types`, `season`, `weeks`, `tournamentId` |
| `https://sports.core.api.espn.com/v2/sports/soccer/leagues/{league}/seasons/{season}/athletes` | `getAthletes` | `active`, `sort`, `page`, `limit`, `seasontypes`, `played`, `teamtypes`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `statuses`, `position` |
| `https://sports.core.api.espn.com/v2/sports/soccer/leagues/{league}/seasons/{season}/draft` | `getDraftByYear` | `page`, `limit`, `available`, `position`, `team`, `sort`, `filter` |
| `https://sports.core.api.espn.com/v2/sports/soccer/leagues/{league}/seasons/{season}/freeagents` | `getFreeAgents` | `page`, `limit`, `types`, `oldteams`, `newteams`, `position`, `sort` |

### Teams

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/soccer/leagues/{league}/teams` | `getTeams` | `page`, `limit`, `active`, `national`, `group`, `dates`, `types` |

### Athletes / Players

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/soccer/leagues/{league}/athletes` | `getAthletes` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |

### Events / Games

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/soccer/leagues/{league}/events/{event}` | `getEvent` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/soccer/leagues/{league}/events/{event}/competitions/{competition}` | `getCompetition` | `page`, `limit`, `date`, `group`, `position`, `week`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/sports/soccer/leagues/{league}/events/{event}/competitions/{competition}/broadcasts` | `getBroadcasts` | `lang`, `region`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/soccer/leagues/{league}/events/{event}/competitions/{competition}/competitors/{competitor}` | `getCompetitor` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/soccer/leagues/{league}/events/{event}/competitions/{competition}/odds` | `getCompetitionOdds` | `provider.priority`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/soccer/leagues/{league}/events/{event}/competitions/{competition}/officials` | `getOfficials` | `page`, `limit` |

### Standings / Rankings / Venues

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/soccer/leagues/{league}/standings` | `getStandings` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/soccer/leagues/{league}/rankings` | `getRankings` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/soccer/leagues/{league}/venues` | `getVenues` | `page`, `limit` |

### News & Media

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/soccer/leagues/{league}/media` | `getMedia` | `page`, `limit` |

### Other

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/soccer/leagues/{league}/countries` | `getCountries` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/soccer/leagues/{league}/franchises` | `getFranchises` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/soccer/leagues/{league}/positions` | `getPositions` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/soccer/leagues/{league}/season` | `getCurrentSeason` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/soccer/leagues/{league}/tournaments` | `getTournaments` | `majorsOnly`, `page`, `limit` |

---

## V3 Endpoints

| Endpoint | Method ID |
| --- | --- |
| `https://sports.core.api.espn.com/v3/sports/soccer/{league}` | `getLeague` |
| `https://sports.core.api.espn.com/v3/sports/soccer/{league}/athletes` | `getAthletes` |
| `https://sports.core.api.espn.com/v3/sports/soccer/{league}/seasons/{season}` | `getSeason` |

---

## Site API Endpoints

> These use `site.api.espn.com` and return user-friendly data.

```
GET https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/{resource}
```

| Resource | Description |
|----------|-------------|
| `scoreboard` | Live scores & schedules |
| `scoreboard?dates={YYYYMMDD}` | Scores for a specific date |
| `teams` | All teams in the league |
| `teams/{id}` | Single team details |
| `teams/{id}/roster` | Team squad |
| `teams/{id}/injuries` | Injury report |
| `teams/{id}/schedule` | Team schedule |
| `standings` | League table — returns empty `{}` on `/apis/site/v2/`, use `/apis/v2/` instead (see below) |
| `news` | Latest match & transfer news |
| `summary?event={id}` | Full match report |

> ⚠️ **Standings Note:** The `/apis/site/v2/` path returns an empty `{}` for soccer standings. Use `/apis/v2/` instead:
> - `https://site.api.espn.com/apis/v2/sports/soccer/{league}/standings`
> - `https://site.web.api.espn.com/apis/v2/sports/soccer/{league}/standings`
> Both return full standings data including team stats, form, and rankings.

---

## Specialized Endpoints

### Live Match Stats (Core API)

```bash
# Match play-by-play (goals, cards, subs)
curl "https://sports.core.api.espn.com/v2/sports/soccer/leagues/eng.1/events/{id}/competitions/{id}/plays?limit=300"

# Live match situation (possession, in-game context)
curl "https://sports.core.api.espn.com/v2/sports/soccer/leagues/eng.1/events/{id}/competitions/{id}/situation"

# Win probability
curl "https://sports.core.api.espn.com/v2/sports/soccer/leagues/eng.1/events/{id}/competitions/{id}/probabilities"

# Match odds
curl "https://sports.core.api.espn.com/v2/sports/soccer/leagues/eng.1/events/{id}/competitions/{id}/odds"
```

### Standings with Groups

```bash
# Full EPL table (points, GD, form) — /apis/site/v2/ returns empty {}, use /apis/v2/
curl "https://site.api.espn.com/apis/v2/sports/soccer/eng.1/standings"

# Alternative domain (identical response)
curl "https://site.web.api.espn.com/apis/v2/sports/soccer/eng.1/standings"

# UCL group stage standings
curl "https://site.api.espn.com/apis/v2/sports/soccer/uefa.champions/standings"

# Core API standings (reference data)
curl "https://sports.core.api.espn.com/v2/sports/soccer/leagues/eng.1/standings"
```

### Top Scorers & Leaders

```bash
# Premier League top scorers / leaders
curl "https://sports.core.api.espn.com/v2/sports/soccer/leagues/eng.1/leaders"

# Season-specific leaders
curl "https://sports.core.api.espn.com/v2/sports/soccer/leagues/eng.1/seasons/2025/leaders"
```

---

## CDN Game Data

> Rich game packages via `cdn.espn.com`. Requires `?xhr=1`.

```bash
# EPL game package (use the specific league name)
curl "https://cdn.espn.com/core/soccer/scoreboard?xhr=1&league=eng.1"
```

---

## Athlete Data (common/v3)

> Individual player stats via `site.web.api.espn.com`. Note: Soccer support is **partially limited** compared to American sports.

| Path | Works |
|------|-------|
| `athletes/{id}/overview` | ⚠️ Returns minimal data (next game only) |
| `athletes/{id}/stats` | ❌ 404 |
| `athletes/{id}/gamelog` | ❌ 400 |
| `athletes/{id}/splits` | ❌ |

> ✅ For full athlete data use **Core API**:
> `sports.core.api.espn.com/v2/sports/soccer/leagues/eng.1/athletes/{id}`
>
> ✅ For active player lists:
> `sports.core.api.espn.com/v3/sports/soccer/eng.1/athletes?limit=100&active=true`

---

## Example API Calls

```bash
# List all soccer leagues
curl "https://sports.core.api.espn.com/v2/sports/soccer/leagues"

# Premier League scoreboard (today)
curl "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard"

# Premier League standings — use /apis/v2/ (site/v2 returns empty {})
curl "https://site.api.espn.com/apis/v2/sports/soccer/eng.1/standings"

# Premier League teams
curl "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/teams"

# UEFA Champions League scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard"

# MLS scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/soccer/usa.1/scoreboard"

# La Liga standings
curl "https://site.api.espn.com/apis/v2/sports/soccer/esp.1/standings"

# Bundesliga scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/soccer/ger.1/scoreboard"

# FIFA World Cup scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"

# Champions League events (core API)
curl "https://sports.core.api.espn.com/v2/sports/soccer/leagues/uefa.champions/events"

# EPL athletes (v3, all active)
curl "https://sports.core.api.espn.com/v3/sports/soccer/eng.1/athletes?limit=100&active=true"

# Arsenal roster
curl "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/teams/359/roster"

# Arsenal injuries
curl "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/teams/359/injuries"

# NWSL scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/soccer/usa.nwsl/scoreboard"

# Women's Champions League scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.wchampions/scoreboard"
```

---

# FILE: `docs/sports/tennis.md`

# 🎾 Tennis

> Professional tennis from the ATP and WTA tours.

**Sport slug:** `tennis`  
**Base URL (v2):** `https://sports.core.api.espn.com/v2/sports/tennis/`  
**Base URL (v3):** `https://sports.core.api.espn.com/v3/sports/tennis/`

---

## Leagues & Competitions

| Abbreviation | League Name | Slug | Full URL |
| --- | --- | --- | --- |
| `ATP` | ATP | `atp` | `https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp` |
| `WTA` | WTA | `wta` | `https://sports.core.api.espn.com/v2/sports/tennis/leagues/wta` |

---

## API Endpoints

> All endpoints below follow the pattern:  
> `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}<sub-path>`  
> Replace `{league}` with a league slug from the table above.

### Common Query Parameters

Most list endpoints support: `page` (int), `limit` (int). Additional filters are documented per endpoint.

### Seasons & Calendar

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/calendar` | `getCalendars` | `dates`, `page`, `limit`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/seasons` | `getSeasons` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/seasons/{season}/athletes` | `getAthletes` | `active`, `sort`, `page`, `limit`, `seasontypes`, `played`, `teamtypes`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/seasons/{season}/draft` | `getDraftByYear` | `page`, `limit`, `available`, `position`, `team`, `sort`, `filter` |
| `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/seasons/{season}/freeagents` | `getFreeAgents` | `page`, `limit`, `types`, `oldteams`, `newteams`, `position`, `sort` |
| `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/seasons/{season}/manufacturers` | `getManufacturers` | `page`, `limit` |

### Teams

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/teams` | `getTeams` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |

### Athletes / Players

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/athletes` | `getAthletes` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |

### Events / Games

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/events/{event}` | `getEvent` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/events/{event}/competitions/{competition}` | `getCompetition` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/events/{event}/competitions/{competition}/broadcasts` | `getBroadcasts` | `lang`, `region`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/events/{event}/competitions/{competition}/competitors/{competitor}` | `getCompetitor` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/events/{event}/competitions/{competition}/odds` | `getCompetitionOdds` | `provider.priority`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/events/{event}/competitions/{competition}/officials` | `getOfficials` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/events/{event}/competitions/{competition}/plays/{play}/personnel` | `getPersonnel` | `page`, `limit` |

### News & Media

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/media` | `getMedia` | `page`, `limit` |

### Rankings & Awards

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/rankings` | `getRankings` | `page`, `limit` |

### Venues

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/venues` | `getVenues` | `page`, `limit` |

### Other

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/casinos` | `getCasinos` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/circuits` | `getCircuits` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/countries` | `getCountries` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/franchises` | `getFranchises` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/positions` | `getPositions` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/providers` | `getProviders` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/recruiting` | `getRecruitingSeasons` | `page`, `limit`, `sort`, `position`, `status` |
| `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/season` | `getCurrentSeason` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/tennis/leagues/{league}/tournaments` | `getTournaments` | `majorsOnly`, `page`, `limit` |

---

## V3 Endpoints

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v3/sports/{sport}/athletes` | `getAthletes` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}` | `getLeague` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}/seasons/{season}` | `getSeason` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |

---

## Site API Endpoints

> These use `site.api.espn.com` and return user-friendly data (scores, rosters, news, etc.)

```
GET https://site.api.espn.com/apis/site/v2/sports/tennis/{league}/{resource}
```

| Resource | Description |
|----------|-------------|
| `scoreboard` | Live match scores |
| `scoreboard?dates={YYYYMMDD}` | Scores for a specific date |
| `teams` | Player groups / tour sections |
| `news` | Latest news |
| `athletes/{id}/news` | Player-specific news |
| `summary?event={id}` | Match summary + results |

> ⚠️ **Slug required:** Tennis scoreboard requires a named league slug — numeric IDs return 400.
> Use: `atp`, `wta` (and potentially `atp-challenger`, `itf`)

> ⚠️ **Injuries endpoint returns 500** for Tennis — not supported.

---

## Example API Calls

```bash
# ATP scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard"

# WTA scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/tennis/wta/scoreboard"

# ATP scoreboard for specific date range
curl "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard?dates=20250620-20250707"

# Get all tennis leagues (core API)
curl "https://sports.core.api.espn.com/v2/sports/tennis/leagues"

# ATP athletes (core API)
curl "https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/athletes?limit=100&active=true"

# ATP events (core API)
curl "https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/events"
```

---

# FILE: `docs/sports/volleyball.md`

# 🏐 Volleyball

> NCAA Men's and Women's volleyball.

**Sport slug:** `volleyball`  
**Base URL (v2):** `https://sports.core.api.espn.com/v2/sports/volleyball/`  
**Base URL (v3):** `https://sports.core.api.espn.com/v3/sports/volleyball/`

---

## Leagues & Competitions

| Abbreviation | League Name | Slug | Full URL |
| --- | --- | --- | --- |
| `NCAA MEN'S VOLLEYBALL` | NCAA Men's Volleyball | `mens-college-volleyball` | `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/mens-college-volleyball` |
| `NCAA WOMEN'S VOLLEYBALL` | NCAA Women's Volleyball | `womens-college-volleyball` | `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/womens-college-volleyball` |

---

## API Endpoints

> All endpoints below follow the pattern:  
> `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}<sub-path>`  
> Replace `{league}` with a league slug from the table above.

### Common Query Parameters

Most list endpoints support: `page` (int), `limit` (int). Additional filters are documented per endpoint.

### Seasons & Calendar

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}/calendar` | `getCalendars` | `dates`, `page`, `limit`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}/seasons` | `getSeasons` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}/seasons/{season}/athletes` | `getAthletes` | `active`, `sort`, `page`, `limit`, `seasontypes`, `played`, `teamtypes`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}/seasons/{season}/draft` | `getDraftByYear` | `page`, `limit`, `available`, `position`, `team`, `sort`, `filter` |
| `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}/seasons/{season}/freeagents` | `getFreeAgents` | `page`, `limit`, `types`, `oldteams`, `newteams`, `position`, `sort` |
| `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}/seasons/{season}/manufacturers` | `getManufacturers` | `page`, `limit` |

### Teams

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}/teams` | `getTeams` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |

### Athletes / Players

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}/athletes` | `getAthletes` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |

### Events / Games

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}/events/{event}` | `getEvent` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}/events/{event}/competitions/{competition}` | `getCompetition` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}/events/{event}/competitions/{competition}/broadcasts` | `getBroadcasts` | `lang`, `region`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}/events/{event}/competitions/{competition}/competitors/{competitor}` | `getCompetitor` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}/events/{event}/competitions/{competition}/odds` | `getCompetitionOdds` | `provider.priority`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}/events/{event}/competitions/{competition}/officials` | `getOfficials` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}/events/{event}/competitions/{competition}/plays/{play}/personnel` | `getPersonnel` | `page`, `limit` |

### News & Media

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}/media` | `getMedia` | `page`, `limit` |

### Rankings & Awards

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}/rankings` | `getRankings` | `page`, `limit` |

### Venues

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}/venues` | `getVenues` | `page`, `limit` |

### Other

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}/casinos` | `getCasinos` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}/circuits` | `getCircuits` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}/countries` | `getCountries` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}/franchises` | `getFranchises` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}/positions` | `getPositions` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}/providers` | `getProviders` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}/recruiting` | `getRecruitingSeasons` | `page`, `limit`, `sort`, `position`, `status` |
| `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}/season` | `getCurrentSeason` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/volleyball/leagues/{league}/tournaments` | `getTournaments` | `majorsOnly`, `page`, `limit` |

---

## V3 Endpoints

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v3/sports/{sport}/athletes` | `getAthletes` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}` | `getLeague` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}/seasons/{season}` | `getSeason` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |

---

## Site API Endpoints

> These use `site.api.espn.com` and return user-friendly data (scores, rosters, news, etc.)

```
GET https://site.api.espn.com/apis/site/v2/sports/volleyball/{league}/{resource}
```

| Resource | Description |
|----------|-------------|
| `scoreboard` | Live scores & schedules |
| `teams` | All teams |
| `standings` | Standings |
| `news` | Latest news |

---

## Example API Calls

```bash
# FIVB Women scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/volleyball/fivb.w/scoreboard"

# FIVB Men scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/volleyball/fivb.m/scoreboard"

# Get all volleyball leagues (core API)
curl "https://sports.core.api.espn.com/v2/sports/volleyball/leagues"

# FIVB Women events (core API)
curl "https://sports.core.api.espn.com/v2/sports/volleyball/leagues/fivb.w/events"
```

---

# FILE: `docs/sports/water_polo.md`

# 🤽 Water Polo

> NCAA Men's and Women's water polo.

**Sport slug:** `water-polo`  
**Base URL (v2):** `https://sports.core.api.espn.com/v2/sports/water-polo/`  
**Base URL (v3):** `https://sports.core.api.espn.com/v3/sports/water-polo/`

---

## Leagues & Competitions

| Abbreviation | League Name | Slug | Full URL |
| --- | --- | --- | --- |
| `NCAAM WATER POLO` | NCAA Men's Water Polo | `mens-college-water-polo` | `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/mens-college-water-polo` |
| `NCAAW WATER POLO` | NCAA Women's Water Polo | `womens-college-water-polo` | `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/womens-college-water-polo` |

---

## API Endpoints

> All endpoints below follow the pattern:  
> `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}<sub-path>`  
> Replace `{league}` with a league slug from the table above.

### Common Query Parameters

Most list endpoints support: `page` (int), `limit` (int). Additional filters are documented per endpoint.

### Seasons & Calendar

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}/calendar` | `getCalendars` | `dates`, `page`, `limit`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}/seasons` | `getSeasons` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `dates`, `sort`, `type`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `sort`, `position`, `status`, `sort`, `sortByRanks`, `stats`, `groupId`, `position`, `qualified`, `rookie`, `international`, `category`, `type`, `sort`, `sortByRanks`, `stats`, `groupId`, `qualified`, `category`, `sort`, `groupId`, `allStar`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |
| `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}/seasons/{season}/athletes` | `getAthletes` | `active`, `sort`, `page`, `limit`, `seasontypes`, `played`, `teamtypes`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |
| `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}/seasons/{season}/draft` | `getDraftByYear` | `page`, `limit`, `available`, `position`, `team`, `sort`, `filter` |
| `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}/seasons/{season}/freeagents` | `getFreeAgents` | `page`, `limit`, `types`, `oldteams`, `newteams`, `position`, `sort` |
| `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}/seasons/{season}/manufacturers` | `getManufacturers` | `page`, `limit` |

### Teams

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}/teams` | `getTeams` | `page`, `limit`, `utcOffset`, `dates`, `start`, `end`, `eventsback`, `eventsforward`, `eventsrange`, `eventcompleted`, `groups`, `profile`, `competitions.types`, `types`, `season`, `weeks`, `tournamentId`, `active`, `national`, `start`, `group`, `dates`, `recent`, `types`, `winnertype`, `date`, `eventsback`, `excludestatuses`, `includestatuses`, `dates`, `groups`, `smartdates`, `advance`, `utcOffset`, `weeks`, `seasontype` |

### Athletes / Players

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}/athletes` | `getAthletes` | `page`, `limit`, `group`, `gender`, `types`, `country`, `association`, `lastNameInitial`, `lastName`, `active`, `statuses`, `sort`, `position` |

### Events / Games

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}/events/{event}` | `getEvent` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}/events/{event}/competitions/{competition}` | `getCompetition` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page`, `types`, `period`, `sort`, `source`, `showsubplays` |
| `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}/events/{event}/competitions/{competition}/broadcasts` | `getBroadcasts` | `lang`, `region`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}/events/{event}/competitions/{competition}/competitors/{competitor}` | `getCompetitor` | `page`, `limit`, `date`, `group`, `position`, `week`, `qualified`, `types`, `limit`, `page` |
| `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}/events/{event}/competitions/{competition}/odds` | `getCompetitionOdds` | `provider.priority`, `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}/events/{event}/competitions/{competition}/officials` | `getOfficials` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}/events/{event}/competitions/{competition}/plays/{play}/personnel` | `getPersonnel` | `page`, `limit` |

### News & Media

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}/media` | `getMedia` | `page`, `limit` |

### Rankings & Awards

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}/rankings` | `getRankings` | `page`, `limit` |

### Venues

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}/venues` | `getVenues` | `page`, `limit` |

### Other

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}/casinos` | `getCasinos` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}/circuits` | `getCircuits` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}/countries` | `getCountries` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}/franchises` | `getFranchises` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}/positions` | `getPositions` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}/providers` | `getProviders` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}/recruiting` | `getRecruitingSeasons` | `page`, `limit`, `sort`, `position`, `status` |
| `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}/season` | `getCurrentSeason` | `page`, `limit` |
| `https://sports.core.api.espn.com/v2/sports/water-polo/leagues/{league}/tournaments` | `getTournaments` | `majorsOnly`, `page`, `limit` |

---

## V3 Endpoints

| Endpoint | Method ID | Query Params |
| --- | --- | --- |
| `https://sports.core.api.espn.com/v3/sports/{sport}/athletes` | `getAthletes` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}` | `getLeague` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |
| `https://sports.core.api.espn.com/v3/sports/{sport}/{league}/seasons/{season}` | `getSeason` | `page`, `limit`, `_hoist`, `_help`, `_trace`, `_nocache`, `enable`, `disable`, `pq`, `q`, `page`, `limit`, `lang`, `region`, `utcOffset`, `dates`, `weeks`, `advance`, `event.recurring`, `ids`, `type`, `types`, `seasontypes`, `calendar.type`, `calendar.groups`, `status`, `statuses`, `groups`, `provider`, `provider.priority`, `site`, `league.type`, `split`, `splits`, `record.splits`, `record.seasontype`, `statistic.splits`, `statistic.seasontype`, `statistic.qualified`, `statistic.context`, `sort`, `roster.positions`, `roster.athletes`, `team.athletes`, `powerindex.rundatetimekey`, `eventsback`, `eventsforward`, `eventsrange`, `eventstates`, `eventresults`, `seek`, `tournaments`, `competitions`, `competition.types`, `teams`, `situation.play`, `oldteams`, `newteams`, `played`, `period`, `position`, `filter`, `available`, `active`, `ids.sportware`, `profile`, `opponent`, `eventId`, `homeAway`, `season`, `athlete.position`, `postalCode`, `award.type`, `notes.type`, `tidbit.type`, `networks`, `bets.promotion`, `guids`, `competitors`, `source` |

---

## Site API Endpoints

> These use `site.api.espn.com` and return user-friendly data (scores, rosters, news, etc.)

```
GET https://site.api.espn.com/apis/site/v2/sports/water-polo/{league}/{resource}
```

| Resource | Description |
|----------|-------------|
| `scoreboard` | Live scores & schedules |
| `teams` | All teams |
| `standings` | Standings |
| `news` | Latest news |

---

## Example API Calls

```bash
# FINA Men's Water Polo scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/water-polo/fina.m/scoreboard"

# FINA Women's Water Polo scoreboard
curl "https://site.api.espn.com/apis/site/v2/sports/water-polo/fina.w/scoreboard"

# Get all water polo leagues (core API)
curl "https://sports.core.api.espn.com/v2/sports/water-polo/leagues"

# Events (core API)
curl "https://sports.core.api.espn.com/v2/sports/water-polo/leagues/fina.m/events"
```

---

# FILE: `espn_service/.env.example`

```
# Django Settings
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
CORS_ALLOWED_ORIGINS=http://localhost:3000

# Database
DATABASE_URL=postgres://espn:espn@localhost:5432/espn_service

# Redis / Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
REDIS_URL=redis://localhost:6379/1

# ESPN Client
ESPN_SITE_API_URL=https://site.api.espn.com
ESPN_CORE_API_URL=https://sports.core.api.espn.com
ESPN_TIMEOUT=30.0
ESPN_MAX_RETRIES=3
ESPN_RETRY_BACKOFF=1.0
ESPN_USER_AGENT=ESPN-Service/1.0

# Logging
LOGGING_LEVEL=INFO

# Optional: Sentry (for production error tracking)
SENTRY_DSN=
SENTRY_TRACES_SAMPLE_RATE=0.1
ENVIRONMENT=development

```

---

# FILE: `espn_service/.gitignore`

```
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal
staticfiles/
media/

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
target/

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# pyenv
.python-version

# pipenv
Pipfile.lock

# PEP 582
__pypackages__/

# Celery stuff
celerybeat-schedule
celerybeat.pid

# SageMath parsed files
*.sage.py

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Pyre type checker
.pyre/

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Docker
.docker/

# Node (if any frontend)
node_modules/

# Ruff
.ruff_cache/

```

---

# FILE: `espn_service/.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: check-merge-conflict
      - id: detect-private-key

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.4
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.9.0
    hooks:
      - id: mypy
        additional_dependencies:
          - django-stubs>=4.2
          - djangorestframework-stubs>=3.14
          - types-requests
        args: [--ignore-missing-imports]
        exclude: ^(migrations/|tests/)

  - repo: local
    hooks:
      - id: django-check
        name: Django Check
        entry: python manage.py check
        language: system
        pass_filenames: false
        types: [python]

```

---

# FILE: `espn_service/Dockerfile`

```
# syntax=docker/dockerfile:1

# Build stage
FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir build && \
    pip wheel --no-cache-dir --wheel-dir /app/wheels -e ".[dev]"

# Production stage
FROM python:3.12-slim as production

WORKDIR /app

# Create non-root user
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels and install
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy application code
COPY --chown=appuser:appgroup . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Default command
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "--access-logfile", "-", "--error-logfile", "-"]

```

---

# FILE: `espn_service/Makefile`

```
.PHONY: help install dev test lint format migrate run shell docker-up docker-down docker-build clean celery beat

# Default target
help:
	@echo "ESPN Service - Available Commands"
	@echo ""
	@echo "Development:"
	@echo "  install     Install production dependencies"
	@echo "  dev         Install development dependencies"
	@echo "  run         Run development server"
	@echo "  shell       Open Django shell"
	@echo "  migrate     Run database migrations"
	@echo ""
	@echo "Testing:"
	@echo "  test        Run all tests"
	@echo "  test-cov    Run tests with coverage report"
	@echo "  test-fast   Run tests without coverage"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint        Run linter (ruff)"
	@echo "  format      Format code (ruff)"
	@echo "  typecheck   Run type checker (mypy)"
	@echo "  pre-commit  Run pre-commit hooks"
	@echo ""
	@echo "Docker:"
	@echo "  docker-up   Start all services"
	@echo "  docker-down Stop all services"
	@echo "  docker-build Build Docker images"
	@echo "  docker-logs View logs"
	@echo ""
	@echo "Celery:"
	@echo "  celery      Start Celery worker"
	@echo "  beat        Start Celery beat scheduler"
	@echo ""
	@echo "Data:"
	@echo "  ingest-teams   Ingest teams (SPORT=basketball LEAGUE=nba)"
	@echo "  ingest-scores  Ingest scoreboard (SPORT=basketball LEAGUE=nba DATE=20241215)"

# Installation
install:
	pip install -e .

dev:
	pip install -e ".[dev]"
	pre-commit install

# Development
run:
	python manage.py runserver

shell:
	python manage.py shell

migrate:
	python manage.py makemigrations
	python manage.py migrate

createsuperuser:
	python manage.py createsuperuser

collectstatic:
	python manage.py collectstatic --noinput

# Testing
test:
	pytest

test-cov:
	pytest --cov=apps --cov=clients --cov-report=html --cov-report=term-missing

test-fast:
	pytest --no-cov -x

# Code Quality
lint:
	ruff check .

format:
	ruff format .
	ruff check --fix .

typecheck:
	mypy apps clients

pre-commit:
	pre-commit run --all-files

# Docker
docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-build:
	docker compose build

docker-logs:
	docker compose logs -f

docker-shell:
	docker compose exec web bash

docker-test:
	docker compose exec web pytest

# Celery
celery:
	celery -A config worker -l INFO

beat:
	celery -A config beat -l INFO

# Data Ingestion
SPORT ?= basketball
LEAGUE ?= nba
DATE ?= $(shell date +%Y%m%d)

ingest-teams:
	python manage.py ingest_teams $(SPORT) $(LEAGUE)

ingest-scores:
	python manage.py ingest_scoreboard $(SPORT) $(LEAGUE) --date=$(DATE)

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	rm -rf dist/ build/ *.egg-info/

```

---

# FILE: `espn_service/README.md`

# ESPN Service API

A production-ready Django REST API for ingesting and querying ESPN sports data.

## Features

- **Data Ingestion**: Fetch and persist data from ESPN's public/undocumented API endpoints
- **REST API**: Clean, paginated endpoints for querying teams, events, and games
- **Background Jobs**: Celery tasks for scheduled data refresh
- **Multi-Sport Support**: All 17 ESPN sports — NFL, NBA, MLB, NHL, WNBA, MLS, UFC, PGA, F1, NRL, and more
- **Production-Ready**: Docker, PostgreSQL, Redis, structured logging, health checks

## Quick Start

### Using Docker (Recommended)

```bash
cd espn_service
cp .env.example .env
docker compose up --build

# API: http://localhost:8000
# Docs: http://localhost:8000/api/docs/
```

### Local Development

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -e ".[dev]"
pre-commit install
python manage.py migrate
python manage.py runserver
```

---

## Service API Endpoints

### Health Check

```bash
GET /healthz
```

### Data Ingestion

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/ingest/teams/` | POST | Ingest teams from ESPN |
| `/api/v1/ingest/scoreboard/` | POST | Ingest events/games |

**Request Body:**
```json
{
    "sport": "basketball",
    "league": "nba",
    "date": "20241215"  // Optional for scoreboard
}
```

### Query Data

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/teams/` | GET | List teams (with filters) |
| `/api/v1/teams/{id}/` | GET | Team details |
| `/api/v1/teams/espn/{espn_id}/` | GET | Team by ESPN ID |
| `/api/v1/events/` | GET | List events (with filters) |
| `/api/v1/events/{id}/` | GET | Event details |
| `/api/v1/events/espn/{espn_id}/` | GET | Event by ESPN ID |

**Filter Parameters:**
- `sport` - Filter by sport slug
- `league` - Filter by league slug
- `search` - Search teams by name
- `date` - Filter events by date (YYYY-MM-DD)
- `team` - Filter events by team abbreviation
- `status` - Filter events by status

---

## ESPN API Endpoints Reference

This service consumes ESPN's undocumented public APIs. Below is a reference of available endpoints.

### Base URLs

| Domain | Purpose |
|--------|---------|
| `site.api.espn.com` | Scores, news, teams, standings |
| `sports.core.api.espn.com` | Athletes, stats, odds |
| `cdn.espn.com` | CDN-optimized live data |

### Supported Sports & Leagues

| Sport | League | Sport Slug | League Slug |
|-------|--------|------------|-------------|
| Football | NFL | `football` | `nfl` |
| Football | College | `football` | `college-football` |
| Football | CFL | `football` | `cfl` |
| Football | UFL | `football` | `ufl` |
| Basketball | NBA | `basketball` | `nba` |
| Basketball | WNBA | `basketball` | `wnba` |
| Basketball | NCAAM | `basketball` | `mens-college-basketball` |
| Basketball | NCAAW | `basketball` | `womens-college-basketball` |
| Baseball | MLB | `baseball` | `mlb` |
| Hockey | NHL | `hockey` | `nhl` |
| Soccer | EPL | `soccer` | `eng.1` |
| Soccer | MLS | `soccer` | `usa.1` |
| Soccer | UCL | `soccer` | `uefa.champions` |
| Soccer | 260+ leagues | `soccer` | See [soccer.md](../docs/sports/soccer.md) |
| MMA | UFC | `mma` | `ufc` |
| Golf | PGA | `golf` | `pga` |
| Golf | LPGA | `golf` | `lpga` |
| Golf | LIV | `golf` | `liv` |
| Tennis | ATP | `tennis` | `atp` |
| Tennis | WTA | `tennis` | `wta` |
| Racing | F1 | `racing` | `f1` |
| Racing | IndyCar | `racing` | `irl` |
| Racing | NASCAR Cup | `racing` | `nascar-premier` |
| Rugby Union | World Cup | `rugby` | `164205` |
| Rugby Union | Six Nations | `rugby` | `180659` |
| Rugby League | NRL / Super League | `rugby-league` | `3` |
| Lacrosse | PLL | `lacrosse` | `pll` |
| Lacrosse | NLL | `lacrosse` | `nll` |
| Australian Football | AFL | `australian-football` | `afl` |
| Cricket | ICC T20 | `cricket` | `icc.t20` |
| Cricket | IPL | `cricket` | `ipl` |
| Volleyball | FIVB Women | `volleyball` | `fivb.w` |
| Volleyball | FIVB Men | `volleyball` | `fivb.m` |

### Soccer League Codes

| League | Code |
|--------|------|
| Premier League | `eng.1` |
| La Liga | `esp.1` |
| Bundesliga | `ger.1` |
| Serie A | `ita.1` |
| Ligue 1 | `fra.1` |
| MLS | `usa.1` |
| Champions League | `uefa.champions` |

### ESPN Endpoint Patterns

**Site API (General Data):**
```
https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/{resource}
```

| Resource | Path |
|----------|------|
| Scoreboard | `/scoreboard` |
| Teams | `/teams` |
| Team Detail | `/teams/{id}` |
| Standings | `/standings` |
| News | `/news` |
| Game Summary | `/summary?event={id}` |

**Core API (Detailed Data):**
```
https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/{resource}
```

| Resource | Path |
|----------|------|
| Athletes | `/athletes?limit=1000` |
| Seasons | `/seasons` |
| Events | `/events?dates=2024` |
| Odds | `/events/{id}/competitions/{id}/odds` |

### ESPN Client Configuration

```python
ESPN_CLIENT = {
    "SITE_API_BASE_URL": "https://site.api.espn.com",
    "CORE_API_BASE_URL": "https://sports.core.api.espn.com",
    "TIMEOUT": 30.0,
    "MAX_RETRIES": 3,
    "RETRY_BACKOFF": 1.0,
}
```

---

## Example Commands

### curl Examples

```bash
# Ingest NBA teams
curl -X POST http://localhost:8000/api/v1/ingest/teams/ \
  -H "Content-Type: application/json" \
  -d '{"sport": "basketball", "league": "nba"}'

# Ingest NFL scoreboard
curl -X POST http://localhost:8000/api/v1/ingest/scoreboard/ \
  -H "Content-Type: application/json" \
  -d '{"sport": "football", "league": "nfl"}'

# Query teams
curl "http://localhost:8000/api/v1/teams/?league=nba"
curl "http://localhost:8000/api/v1/teams/?search=Lakers"

# Query events
curl "http://localhost:8000/api/v1/events/?league=nba&date=2024-12-15"
curl "http://localhost:8000/api/v1/events/?team=LAL&status=final"

# Health check
curl http://localhost:8000/healthz
```

### Management Commands

```bash
# Ingest teams for a single league
python manage.py ingest_teams basketball nba

# Ingest scoreboard for a single league
python manage.py ingest_scoreboard basketball nba --date=20241215

# Ingest teams for ALL 17 sports (40+ leagues)
python manage.py ingest_all_teams

# Filter to a single sport
python manage.py ingest_all_teams --sport soccer

# Preview what would run without ingesting
python manage.py ingest_all_teams --dry-run
```

---

## Celery Background Jobs

```bash
# Start worker
celery -A config worker -l INFO

# Start scheduler
celery -A config beat -l INFO
```

### Scheduled Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| `refresh_scoreboard_task` | On-demand | Refresh scoreboard for a specific sport/league/date |
| `refresh_teams_task` | On-demand | Refresh teams for a specific sport/league |
| `refresh_all_teams_task` | Weekly | Refresh all team data (40+ leagues, all 17 sports) |
| `refresh_daily_scoreboards_task` | Hourly | Refresh today's scoreboards (40+ leagues, all 17 sports) |

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | Required in prod |
| `DEBUG` | Debug mode | `False` |
| `DATABASE_URL` | PostgreSQL URL | sqlite for local |
| `CELERY_BROKER_URL` | Redis URL | `redis://localhost:6379/0` |
| `ESPN_TIMEOUT` | API timeout (sec) | `30.0` |
| `ESPN_MAX_RETRIES` | Max retries | `3` |
| `ALLOWED_HOSTS` | Allowed hosts | `localhost,127.0.0.1` |

---

## Project Structure

```
espn_service/
├── config/                # Django configuration
│   ├── settings/
│   │   ├── base.py       # Base settings
│   │   ├── local.py      # Local development
│   │   ├── production.py # Production
│   │   └── test.py       # Test settings
│   ├── celery.py         # Celery config
│   └── urls.py           # URL routing
├── apps/
│   ├── core/             # Core utilities
│   ├── espn/             # ESPN data models & API
│   └── ingest/           # Data ingestion
├── clients/
│   └── espn_client.py    # ESPN API client
├── tests/                # Test suite
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## Database Models

| Model | Description |
|-------|-------------|
| `Sport` | Sport types (basketball, football) |
| `League` | Leagues within sports (NBA, NFL) |
| `Team` | Team info with logos, colors |
| `Venue` | Stadium/arena information |
| `Event` | Games with status, scores |
| `Competitor` | Team participation in events |
| `Athlete` | Player information |

---

## Testing

```bash
# All tests with coverage
make test

# Quick tests
make test-fast

# Specific file
pytest tests/test_api.py -v
```

---

## Production Deployment

### Docker Production

```bash
docker compose -f docker-compose.prod.yml up -d
```

### Cloud Platforms

**AWS ECS/Fargate:**
```bash
docker build -t espn-service:latest .
docker push <account>.dkr.ecr.<region>.amazonaws.com/espn-service:latest
```

**Google Cloud Run:**
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/espn-service
gcloud run deploy espn-service --image gcr.io/PROJECT_ID/espn-service
```

**Fly.io:**
```bash
fly launch
fly secrets set SECRET_KEY=your-key DATABASE_URL=your-url
fly deploy
```

---

## API Documentation

Once running:
- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

---

## License

MIT License - See LICENSE file

---

# FILE: `espn_service/apps/__init__.py`

```python
# Apps package

```

---

# FILE: `espn_service/apps/core/__init__.py`

```python
# Core app

```

---

# FILE: `espn_service/apps/core/apps.py`

```python
"""Core app configuration."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Core application configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Core"

```

---

# FILE: `espn_service/apps/core/exceptions.py`

```python
"""Custom exception handling for the API."""

from typing import Any

import structlog
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = structlog.get_logger(__name__)


class ESPNServiceError(APIException):
    """Base exception for ESPN service errors."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "An internal error occurred."
    default_code = "internal_error"


class ESPNClientError(ESPNServiceError):
    """Error communicating with ESPN API."""

    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "Error communicating with ESPN API."
    default_code = "espn_client_error"


class ESPNRateLimitError(ESPNClientError):
    """ESPN API rate limit exceeded."""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "ESPN API rate limit exceeded. Please try again later."
    default_code = "espn_rate_limit"


class ESPNNotFoundError(ESPNClientError):
    """ESPN resource not found."""

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Resource not found in ESPN API."
    default_code = "espn_not_found"


class IngestionError(ESPNServiceError):
    """Error during data ingestion."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Error during data ingestion."
    default_code = "ingestion_error"


class ValidationError(ESPNServiceError):
    """Validation error for API requests."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid request data."
    default_code = "validation_error"


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """Custom exception handler for DRF that adds structured error responses."""
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    # Log the exception
    logger.error(
        "api_exception",
        exc_type=type(exc).__name__,
        exc_message=str(exc),
        view=context.get("view").__class__.__name__ if context.get("view") else None,
    )

    if response is not None:
        # Enhance error response with structured format
        error_data = {
            "error": {
                "code": getattr(exc, "default_code", "error"),
                "message": str(exc.detail) if hasattr(exc, "detail") else str(exc),
                "status": response.status_code,
            }
        }

        # Add field errors for validation exceptions
        if hasattr(exc, "detail") and isinstance(exc.detail, dict):
            error_data["error"]["fields"] = exc.detail

        response.data = error_data
        return response

    # Handle Django-specific exceptions
    if isinstance(exc, Http404):
        return Response(
            {
                "error": {
                    "code": "not_found",
                    "message": "Resource not found.",
                    "status": 404,
                }
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    if isinstance(exc, DjangoValidationError):
        return Response(
            {
                "error": {
                    "code": "validation_error",
                    "message": str(exc),
                    "status": 400,
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # For unhandled exceptions, return a generic error
    logger.exception("unhandled_exception", exc=exc)
    return Response(
        {
            "error": {
                "code": "internal_error",
                "message": "An internal error occurred.",
                "status": 500,
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

```

---

# FILE: `espn_service/apps/core/middleware.py`

```python
"""Core middleware for request handling."""

import time
import uuid
from collections.abc import Callable

import structlog
from django.http import HttpRequest, HttpResponse

logger = structlog.get_logger(__name__)


class RequestIDMiddleware:
    """Add unique request ID to each request for tracing."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.request_id = request_id  # type: ignore[attr-defined]

        # Bind request ID to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = self.get_response(request)

        # Add request ID to response headers
        response["X-Request-ID"] = request_id

        return response


class StructuredLoggingMiddleware:
    """Log request/response information in a structured format."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Skip logging for health checks
        if request.path == "/healthz":
            return self.get_response(request)

        start_time = time.perf_counter()

        # Log incoming request
        logger.info(
            "request_started",
            method=request.method,
            path=request.path,
            query_params=dict(request.GET),
            user_agent=request.headers.get("User-Agent", ""),
        )

        response = self.get_response(request)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Log response
        logger.info(
            "request_finished",
            method=request.method,
            path=request.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

        return response

```

---

# FILE: `espn_service/apps/core/views.py`

```python
"""Core views including health checks."""

from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """Health check endpoint for container orchestration."""

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["Health"],
        summary="Health check",
        description="Check service health and database connectivity.",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "example": "healthy"},
                    "database": {"type": "string", "example": "connected"},
                },
            },
            503: {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "example": "unhealthy"},
                    "database": {"type": "string", "example": "disconnected"},
                    "error": {"type": "string"},
                },
            },
        },
    )
    def get(self, request: Request) -> Response:  # noqa: ARG002
        """Return health status including database connectivity."""
        health_status = {
            "status": "healthy",
            "database": "connected",
        }

        try:
            # Check database connectivity
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["database"] = "disconnected"
            health_status["error"] = str(e)
            return Response(health_status, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(health_status, status=status.HTTP_200_OK)

```

---

# FILE: `espn_service/apps/espn/__init__.py`

```python
# ESPN app

```

---

# FILE: `espn_service/apps/espn/admin.py`

```python
"""Django admin configuration for ESPN models."""

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.html import format_html

from apps.espn.models import (
    Athlete,
    AthleteSeasonStats,
    Competitor,
    Event,
    Injury,
    League,
    NewsArticle,
    Sport,
    Team,
    Transaction,
    Venue,
)


@admin.register(Sport)
class SportAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "league_count", "created_at"]
    search_fields = ["name", "slug"]
    readonly_fields = ["created_at", "updated_at"]

    def league_count(self, obj: Sport) -> int:
        return obj.leagues.count()

    league_count.short_description = "Leagues"  # type: ignore[attr-defined]


@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ["name", "abbreviation", "sport", "team_count", "created_at"]
    list_filter = ["sport"]
    search_fields = ["name", "slug", "abbreviation"]
    readonly_fields = ["created_at", "updated_at"]

    def team_count(self, obj: League) -> int:
        return obj.teams.count()

    team_count.short_description = "Teams"  # type: ignore[attr-defined]


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ["display_name", "abbreviation", "league", "espn_id", "is_active", "color_preview"]
    list_filter = ["league", "is_active", "is_all_star"]
    search_fields = ["display_name", "abbreviation", "espn_id", "slug"]
    readonly_fields = ["created_at", "updated_at", "logo_preview"]

    def color_preview(self, obj: Team) -> str:
        if obj.color:
            return format_html(
                '<span style="background-color: #{0}; padding: 2px 10px; '
                'border-radius: 3px; color: white;">{0}</span>',
                obj.color,
            )
        return "-"

    color_preview.short_description = "Color"  # type: ignore[attr-defined]

    def logo_preview(self, obj: Team) -> str:
        logo_url = obj.primary_logo
        if logo_url:
            return format_html(
                '<img src="{0}" style="max-height: 100px; max-width: 100px;" />',
                logo_url,
            )
        return "-"

    logo_preview.short_description = "Logo"  # type: ignore[attr-defined]


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ["name", "city", "state", "is_indoor", "capacity", "espn_id"]
    list_filter = ["is_indoor", "state", "country"]
    search_fields = ["name", "city", "espn_id"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["short_name", "league", "date", "status", "venue", "espn_id"]
    list_filter = ["league", "status", "season_year", "season_type"]
    search_fields = ["name", "short_name", "espn_id"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "date"

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).select_related("league", "venue")


@admin.register(Competitor)
class CompetitorAdmin(admin.ModelAdmin):
    list_display = ["team", "event", "home_away", "score", "winner"]
    list_filter = ["home_away", "winner", "event__league"]
    search_fields = ["team__display_name", "event__name"]
    readonly_fields = ["created_at", "updated_at"]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).select_related("team", "event")


@admin.register(Athlete)
class AthleteAdmin(admin.ModelAdmin):
    list_display = ["display_name", "team", "position", "jersey", "is_active", "espn_id"]
    list_filter = ["is_active", "team__league", "position"]
    search_fields = ["full_name", "display_name", "espn_id"]
    readonly_fields = ["created_at", "updated_at", "headshot_preview"]

    def headshot_preview(self, obj: Athlete) -> str:
        if obj.headshot:
            return format_html(
                '<img src="{0}" style="max-height: 100px; max-width: 100px;" />',
                obj.headshot,
            )
        return "-"

    headshot_preview.short_description = "Headshot"  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# New model admins — added in audit expansion
# ---------------------------------------------------------------------------


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    """Admin for NewsArticle model."""

    list_display = ["headline_truncated", "type", "league", "published", "created_at"]
    list_filter = ["type", "league__sport", "league"]
    search_fields = ["headline", "description", "espn_id"]
    readonly_fields = ["created_at", "updated_at", "thumbnail_preview"]
    date_hierarchy = "published"

    def headline_truncated(self, obj: NewsArticle) -> str:
        return obj.headline[:60] + "…" if len(obj.headline) > 60 else obj.headline

    headline_truncated.short_description = "Headline"  # type: ignore[attr-defined]

    def thumbnail_preview(self, obj: NewsArticle) -> str:
        url = obj.thumbnail
        if url:
            return format_html('<img src="{0}" style="max-height: 80px;" />', url)
        return "-"

    thumbnail_preview.short_description = "Thumbnail"  # type: ignore[attr-defined]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).select_related("league", "league__sport")


@admin.register(Injury)
class InjuryAdmin(admin.ModelAdmin):
    """Admin for Injury model."""

    list_display = [
        "athlete_name",
        "position",
        "status",
        "injury_type",
        "team",
        "league",
        "updated_at",
    ]
    list_filter = ["status", "league__sport", "league"]
    search_fields = ["athlete_name", "injury_type", "description", "athlete_espn_id"]
    readonly_fields = ["created_at", "updated_at"]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).select_related("league", "league__sport", "team")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Admin for Transaction model."""

    list_display = ["description_truncated", "type", "athlete_name", "team", "league", "date"]
    list_filter = ["type", "league__sport", "league"]
    search_fields = ["description", "athlete_name", "espn_id", "athlete_espn_id"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "date"

    def description_truncated(self, obj: Transaction) -> str:
        return obj.description[:60] + "…" if len(obj.description) > 60 else obj.description

    description_truncated.short_description = "Description"  # type: ignore[attr-defined]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).select_related("league", "league__sport", "team")


@admin.register(AthleteSeasonStats)
class AthleteSeasonStatsAdmin(admin.ModelAdmin):
    """Admin for AthleteSeasonStats model."""

    list_display = [
        "athlete_name",
        "athlete_espn_id",
        "league",
        "season_year",
        "season_type",
        "updated_at",
    ]
    list_filter = ["season_year", "season_type", "league__sport", "league"]
    search_fields = ["athlete_name", "athlete_espn_id"]
    readonly_fields = ["created_at", "updated_at"]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return (
            super().get_queryset(request).select_related("league", "league__sport", "athlete")
        )

```

---

# FILE: `espn_service/apps/espn/apps.py`

```python
"""ESPN app configuration."""

from django.apps import AppConfig


class ESPNConfig(AppConfig):
    """ESPN application configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.espn"
    verbose_name = "ESPN"

```

---

# FILE: `espn_service/apps/espn/filters.py`

```python
"""Filters for ESPN data API endpoints."""

import django_filters
from django.db.models import Q, QuerySet

from apps.espn.models import Event, Team


class TeamFilter(django_filters.FilterSet):
    """Filter for Team queryset."""

    sport = django_filters.CharFilter(
        field_name="league__sport__slug",
        lookup_expr="iexact",
        help_text="Filter by sport slug (e.g., 'basketball')",
    )
    league = django_filters.CharFilter(
        field_name="league__slug",
        lookup_expr="iexact",
        help_text="Filter by league slug (e.g., 'nba')",
    )
    is_active = django_filters.BooleanFilter(
        help_text="Filter by active status",
    )
    abbreviation = django_filters.CharFilter(
        lookup_expr="iexact",
        help_text="Filter by team abbreviation",
    )
    search = django_filters.CharFilter(
        method="search_filter",
        help_text="Search in display_name, abbreviation, or location",
    )

    class Meta:
        model = Team
        fields = ["sport", "league", "is_active", "abbreviation"]

    def search_filter(
        self, queryset: QuerySet, name: str, value: str  # noqa: ARG002
    ) -> QuerySet:
        """Custom search filter across multiple fields."""
        if not value:
            return queryset
        return queryset.filter(
            Q(display_name__icontains=value)
            | Q(abbreviation__icontains=value)
            | Q(location__icontains=value)
            | Q(name__icontains=value)
        )


class EventFilter(django_filters.FilterSet):
    """Filter for Event queryset."""

    sport = django_filters.CharFilter(
        field_name="league__sport__slug",
        lookup_expr="iexact",
        help_text="Filter by sport slug (e.g., 'basketball')",
    )
    league = django_filters.CharFilter(
        field_name="league__slug",
        lookup_expr="iexact",
        help_text="Filter by league slug (e.g., 'nba')",
    )
    date = django_filters.DateFilter(
        field_name="date",
        lookup_expr="date",
        help_text="Filter by exact date (YYYY-MM-DD)",
    )
    date_from = django_filters.DateFilter(
        field_name="date",
        lookup_expr="date__gte",
        help_text="Filter by date >= (YYYY-MM-DD)",
    )
    date_to = django_filters.DateFilter(
        field_name="date",
        lookup_expr="date__lte",
        help_text="Filter by date <= (YYYY-MM-DD)",
    )
    status = django_filters.ChoiceFilter(
        choices=Event.STATUS_CHOICES,
        help_text="Filter by event status",
    )
    season_year = django_filters.NumberFilter(
        help_text="Filter by season year",
    )
    season_type = django_filters.NumberFilter(
        help_text="Filter by season type (1=preseason, 2=regular, 3=postseason)",
    )
    team = django_filters.CharFilter(
        method="team_filter",
        help_text="Filter by team ESPN ID or abbreviation",
    )

    class Meta:
        model = Event
        fields = [
            "sport",
            "league",
            "date",
            "date_from",
            "date_to",
            "status",
            "season_year",
            "season_type",
        ]

    def team_filter(
        self, queryset: QuerySet, name: str, value: str  # noqa: ARG002
    ) -> QuerySet:
        """Filter events by team (ESPN ID or abbreviation)."""
        if not value:
            return queryset
        return queryset.filter(
            Q(competitors__team__espn_id=value)
            | Q(competitors__team__abbreviation__iexact=value)
        ).distinct()

```

---

# FILE: `espn_service/apps/espn/migrations/0001_initial.py`

```python
# Generated by Django 5.1.6 on 2025-12-18 06:20

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='League',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('slug', models.CharField(db_index=True, max_length=50)),
                ('name', models.CharField(max_length=100)),
                ('abbreviation', models.CharField(blank=True, max_length=20)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Sport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('slug', models.CharField(db_index=True, max_length=50, unique=True)),
                ('name', models.CharField(max_length=100)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Venue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('espn_id', models.CharField(db_index=True, max_length=50, unique=True)),
                ('name', models.CharField(max_length=200)),
                ('city', models.CharField(blank=True, max_length=100)),
                ('state', models.CharField(blank=True, max_length=100)),
                ('country', models.CharField(blank=True, default='USA', max_length=100)),
                ('is_indoor', models.BooleanField(default=True)),
                ('capacity', models.PositiveIntegerField(blank=True, null=True)),
                ('raw_data', models.JSONField(blank=True, default=dict)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('espn_id', models.CharField(db_index=True, max_length=50)),
                ('uid', models.CharField(blank=True, max_length=100)),
                ('date', models.DateTimeField()),
                ('name', models.CharField(max_length=200)),
                ('short_name', models.CharField(blank=True, max_length=100)),
                ('season_year', models.PositiveIntegerField()),
                ('season_type', models.PositiveSmallIntegerField(default=2)),
                ('season_slug', models.CharField(blank=True, max_length=50)),
                ('week', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('status', models.CharField(choices=[('scheduled', 'Scheduled'), ('in_progress', 'In Progress'), ('final', 'Final'), ('postponed', 'Postponed'), ('cancelled', 'Cancelled')], default='scheduled', max_length=20)),
                ('status_detail', models.CharField(blank=True, max_length=100)),
                ('clock', models.CharField(blank=True, max_length=20)),
                ('period', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('attendance', models.PositiveIntegerField(blank=True, null=True)),
                ('broadcasts', models.JSONField(blank=True, default=list)),
                ('links', models.JSONField(blank=True, default=list)),
                ('raw_data', models.JSONField(blank=True, default=dict)),
                ('league', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='espn.league')),
                ('venue', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='events', to='espn.venue')),
            ],
            options={
                'ordering': ['-date'],
                'unique_together': {('league', 'espn_id')},
            },
        ),
        migrations.AddField(
            model_name='league',
            name='sport',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='leagues', to='espn.sport'),
        ),
        migrations.CreateModel(
            name='Team',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('espn_id', models.CharField(db_index=True, max_length=50)),
                ('uid', models.CharField(blank=True, max_length=100)),
                ('slug', models.CharField(blank=True, max_length=100)),
                ('abbreviation', models.CharField(max_length=10)),
                ('display_name', models.CharField(max_length=100)),
                ('short_display_name', models.CharField(blank=True, max_length=50)),
                ('name', models.CharField(blank=True, max_length=50)),
                ('nickname', models.CharField(blank=True, max_length=50)),
                ('location', models.CharField(blank=True, max_length=100)),
                ('color', models.CharField(blank=True, max_length=10)),
                ('alternate_color', models.CharField(blank=True, max_length=10)),
                ('is_active', models.BooleanField(default=True)),
                ('is_all_star', models.BooleanField(default=False)),
                ('logos', models.JSONField(blank=True, default=list)),
                ('links', models.JSONField(blank=True, default=list)),
                ('raw_data', models.JSONField(blank=True, default=dict)),
                ('league', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='teams', to='espn.league')),
            ],
            options={
                'ordering': ['display_name'],
                'unique_together': {('league', 'espn_id')},
            },
        ),
        migrations.CreateModel(
            name='Athlete',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('espn_id', models.CharField(db_index=True, max_length=50, unique=True)),
                ('uid', models.CharField(blank=True, max_length=100)),
                ('first_name', models.CharField(max_length=50)),
                ('last_name', models.CharField(max_length=50)),
                ('full_name', models.CharField(max_length=100)),
                ('display_name', models.CharField(max_length=100)),
                ('short_name', models.CharField(blank=True, max_length=50)),
                ('position', models.CharField(blank=True, max_length=50)),
                ('position_abbreviation', models.CharField(blank=True, max_length=10)),
                ('jersey', models.CharField(blank=True, max_length=10)),
                ('is_active', models.BooleanField(default=True)),
                ('height', models.CharField(blank=True, max_length=20)),
                ('weight', models.PositiveIntegerField(blank=True, null=True)),
                ('age', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('birth_date', models.DateField(blank=True, null=True)),
                ('birth_place', models.CharField(blank=True, max_length=100)),
                ('headshot', models.URLField(blank=True, max_length=500)),
                ('links', models.JSONField(blank=True, default=list)),
                ('raw_data', models.JSONField(blank=True, default=dict)),
                ('team', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='athletes', to='espn.team')),
            ],
            options={
                'ordering': ['last_name', 'first_name'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='league',
            unique_together={('sport', 'slug')},
        ),
        migrations.CreateModel(
            name='Competitor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('home_away', models.CharField(choices=[('home', 'Home'), ('away', 'Away')], max_length=4)),
                ('score', models.CharField(blank=True, max_length=10)),
                ('winner', models.BooleanField(blank=True, null=True)),
                ('line_scores', models.JSONField(blank=True, default=list)),
                ('records', models.JSONField(blank=True, default=list)),
                ('statistics', models.JSONField(blank=True, default=list)),
                ('leaders', models.JSONField(blank=True, default=list)),
                ('order', models.PositiveSmallIntegerField(default=0)),
                ('raw_data', models.JSONField(blank=True, default=dict)),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='competitors', to='espn.event')),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='competitions', to='espn.team')),
            ],
            options={
                'ordering': ['order'],
                'unique_together': {('event', 'team')},
            },
        ),
    ]

```

---

# FILE: `espn_service/apps/espn/migrations/0002_injury_newsarticle_transaction_athleteseasonstats.py`

```python
# Generated by Django 5.2.12 on 2026-03-23 13:22

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('espn', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Injury',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('espn_id', models.CharField(blank=True, db_index=True, max_length=100)),
                ('athlete_espn_id', models.CharField(blank=True, db_index=True, max_length=50)),
                ('athlete_name', models.CharField(max_length=100)),
                ('position', models.CharField(blank=True, max_length=50)),
                ('status', models.CharField(choices=[('out', 'Out'), ('questionable', 'Questionable'), ('doubtful', 'Doubtful'), ('ir', 'IR'), ('day_to_day', 'Day-to-Day'), ('other', 'Other')], db_index=True, default='other', max_length=20)),
                ('status_display', models.CharField(blank=True, max_length=100)),
                ('description', models.CharField(blank=True, max_length=500)),
                ('injury_type', models.CharField(blank=True, max_length=100)),
                ('injury_date', models.DateField(blank=True, null=True)),
                ('return_date', models.DateField(blank=True, null=True)),
                ('raw_data', models.JSONField(blank=True, default=dict)),
                ('league', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='injuries', to='espn.league')),
                ('team', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='injuries', to='espn.team')),
            ],
            options={
                'verbose_name': 'Injury',
                'verbose_name_plural': 'Injuries',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='NewsArticle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('espn_id', models.CharField(db_index=True, max_length=100, unique=True)),
                ('headline', models.CharField(max_length=500)),
                ('description', models.TextField(blank=True)),
                ('story', models.TextField(blank=True)),
                ('published', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('last_modified', models.DateTimeField(blank=True, null=True)),
                ('type', models.CharField(blank=True, max_length=50)),
                ('categories', models.JSONField(blank=True, default=list)),
                ('images', models.JSONField(blank=True, default=list)),
                ('links', models.JSONField(blank=True, default=dict)),
                ('raw_data', models.JSONField(blank=True, default=dict)),
                ('league', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='news_articles', to='espn.league')),
            ],
            options={
                'verbose_name': 'News Article',
                'verbose_name_plural': 'News Articles',
                'ordering': ['-published'],
            },
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('espn_id', models.CharField(blank=True, db_index=True, max_length=100)),
                ('date', models.DateField(blank=True, db_index=True, null=True)),
                ('description', models.TextField()),
                ('type', models.CharField(blank=True, max_length=100)),
                ('athlete_name', models.CharField(blank=True, max_length=100)),
                ('athlete_espn_id', models.CharField(blank=True, db_index=True, max_length=50)),
                ('raw_data', models.JSONField(blank=True, default=dict)),
                ('league', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='espn.league')),
                ('team', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transactions', to='espn.team')),
            ],
            options={
                'verbose_name': 'Transaction',
                'verbose_name_plural': 'Transactions',
                'ordering': ['-date', '-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='AthleteSeasonStats',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('athlete_espn_id', models.CharField(db_index=True, max_length=50)),
                ('athlete_name', models.CharField(blank=True, max_length=100)),
                ('season_year', models.PositiveIntegerField(db_index=True)),
                ('season_type', models.PositiveSmallIntegerField(default=2)),
                ('stats', models.JSONField(blank=True, default=dict)),
                ('raw_data', models.JSONField(blank=True, default=dict)),
                ('athlete', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='season_stats', to='espn.athlete')),
                ('league', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='athlete_season_stats', to='espn.league')),
            ],
            options={
                'verbose_name': 'Athlete Season Stats',
                'verbose_name_plural': 'Athlete Season Stats',
                'ordering': ['-season_year'],
                'unique_together': {('league', 'athlete_espn_id', 'season_year', 'season_type')},
            },
        ),
    ]

```

---

# FILE: `espn_service/apps/espn/migrations/__init__.py`

```python

```

---

# FILE: `espn_service/apps/espn/models.py`

```python
"""Database models for ESPN sports data."""

from django.db import models


class TimestampMixin(models.Model):
    """Mixin providing created_at and updated_at timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Sport(TimestampMixin):
    """Sport entity (e.g., basketball, football)."""

    slug = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class League(TimestampMixin):
    """League entity (e.g., NBA, NFL)."""

    sport = models.ForeignKey(
        Sport,
        on_delete=models.CASCADE,
        related_name="leagues",
    )
    slug = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=100)
    abbreviation = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["name"]
        unique_together = [["sport", "slug"]]

    def __str__(self) -> str:
        return f"{self.name} ({self.sport.name})"


class Venue(TimestampMixin):
    """Venue/stadium entity."""

    espn_id = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True, default="USA")
    is_indoor = models.BooleanField(default=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)

    # Raw data for extensibility
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        location = ", ".join(filter(None, [self.city, self.state]))
        return f"{self.name} ({location})" if location else self.name


class Team(TimestampMixin):
    """Team entity."""

    league = models.ForeignKey(
        League,
        on_delete=models.CASCADE,
        related_name="teams",
    )
    espn_id = models.CharField(max_length=50, db_index=True)
    uid = models.CharField(max_length=100, blank=True)
    slug = models.CharField(max_length=100, blank=True)
    abbreviation = models.CharField(max_length=10)
    display_name = models.CharField(max_length=100)
    short_display_name = models.CharField(max_length=50, blank=True)
    name = models.CharField(max_length=50, blank=True)  # Team name only (e.g., "Lakers")
    nickname = models.CharField(max_length=50, blank=True)  # City/location
    location = models.CharField(max_length=100, blank=True)
    color = models.CharField(max_length=10, blank=True)
    alternate_color = models.CharField(max_length=10, blank=True)
    is_active = models.BooleanField(default=True)
    is_all_star = models.BooleanField(default=False)

    # Store logo URLs and other semi-structured data
    logos = models.JSONField(default=list, blank=True)
    links = models.JSONField(default=list, blank=True)

    # Raw data for extensibility
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["display_name"]
        unique_together = [["league", "espn_id"]]

    def __str__(self) -> str:
        return f"{self.display_name} ({self.league.slug.upper()})"

    @property
    def primary_logo(self) -> str | None:
        """Get the primary logo URL."""
        if not self.logos:
            return None
        # Look for default logo first
        for logo in self.logos:
            if isinstance(logo, dict) and "default" in logo.get("rel", []):
                return logo.get("href")
        # Fallback to first logo
        if self.logos and isinstance(self.logos[0], dict):
            return self.logos[0].get("href")
        return None


class Event(TimestampMixin):
    """Event/game entity."""

    league = models.ForeignKey(
        League,
        on_delete=models.CASCADE,
        related_name="events",
    )
    venue = models.ForeignKey(
        Venue,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )
    espn_id = models.CharField(max_length=50, db_index=True)
    uid = models.CharField(max_length=100, blank=True)
    date = models.DateTimeField()
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=100, blank=True)

    # Season information
    season_year = models.PositiveIntegerField()
    season_type = models.PositiveSmallIntegerField(default=2)  # 1=preseason, 2=regular, 3=postseason
    season_slug = models.CharField(max_length=50, blank=True)
    week = models.PositiveSmallIntegerField(null=True, blank=True)

    # Status
    STATUS_SCHEDULED = "scheduled"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_FINAL = "final"
    STATUS_POSTPONED = "postponed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_SCHEDULED, "Scheduled"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_FINAL, "Final"),
        (STATUS_POSTPONED, "Postponed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_SCHEDULED,
    )
    status_detail = models.CharField(max_length=100, blank=True)
    clock = models.CharField(max_length=20, blank=True)
    period = models.PositiveSmallIntegerField(null=True, blank=True)

    # Attendance
    attendance = models.PositiveIntegerField(null=True, blank=True)

    # Broadcasts
    broadcasts = models.JSONField(default=list, blank=True)

    # Links
    links = models.JSONField(default=list, blank=True)

    # Raw data for extensibility
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-date"]
        unique_together = [["league", "espn_id"]]

    def __str__(self) -> str:
        return f"{self.short_name or self.name} ({self.date.strftime('%Y-%m-%d')})"


class Competitor(TimestampMixin):
    """Competitor in an event (links team to event with game-specific data)."""

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="competitors",
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="competitions",
    )

    # Home/away designation
    HOME = "home"
    AWAY = "away"
    HOME_AWAY_CHOICES = [
        (HOME, "Home"),
        (AWAY, "Away"),
    ]
    home_away = models.CharField(
        max_length=4,
        choices=HOME_AWAY_CHOICES,
    )

    # Score and result
    score = models.CharField(max_length=10, blank=True)
    winner = models.BooleanField(null=True, blank=True)

    # Line scores (quarter/period scores)
    line_scores = models.JSONField(default=list, blank=True)

    # Records (overall, home, away)
    records = models.JSONField(default=list, blank=True)

    # Statistics
    statistics = models.JSONField(default=list, blank=True)

    # Leaders (points, rebounds, assists leaders)
    leaders = models.JSONField(default=list, blank=True)

    # Order (usually 0 for away, 1 for home)
    order = models.PositiveSmallIntegerField(default=0)

    # Raw data for extensibility
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["order"]
        unique_together = [["event", "team"]]

    def __str__(self) -> str:
        return f"{self.team.abbreviation} ({self.home_away}) - {self.event.short_name}"

    @property
    def score_int(self) -> int | None:
        """Get score as integer."""
        try:
            return int(self.score) if self.score else None
        except ValueError:
            return None


class Athlete(TimestampMixin):
    """Athlete entity (optional - for detailed stats)."""

    espn_id = models.CharField(max_length=50, unique=True, db_index=True)
    uid = models.CharField(max_length=100, blank=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    full_name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=100)
    short_name = models.CharField(max_length=50, blank=True)

    # Current team (nullable - athletes can be free agents)
    team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="athletes",
    )

    # Position
    position = models.CharField(max_length=50, blank=True)
    position_abbreviation = models.CharField(max_length=10, blank=True)

    # Jersey
    jersey = models.CharField(max_length=10, blank=True)

    # Status
    is_active = models.BooleanField(default=True)

    # Physical attributes
    height = models.CharField(max_length=20, blank=True)  # e.g., "6'8"
    weight = models.PositiveIntegerField(null=True, blank=True)  # in pounds
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    birth_place = models.CharField(max_length=100, blank=True)

    # Media
    headshot = models.URLField(max_length=500, blank=True)

    # Links
    links = models.JSONField(default=list, blank=True)

    # Raw data for extensibility
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        team_abbr = self.team.abbreviation if self.team else "FA"
        return f"{self.display_name} ({team_abbr})"


# ---------------------------------------------------------------------------
# New models — added in audit expansion
# ---------------------------------------------------------------------------


class NewsArticle(TimestampMixin):
    """News article from ESPN news or Now API."""

    espn_id = models.CharField(max_length=100, unique=True, db_index=True)
    headline = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    story = models.TextField(blank=True)
    published = models.DateTimeField(null=True, blank=True, db_index=True)
    last_modified = models.DateTimeField(null=True, blank=True)
    type = models.CharField(max_length=50, blank=True)

    # Optional league association (nullable — some articles span multiple leagues)
    league = models.ForeignKey(
        League,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="news_articles",
    )

    categories = models.JSONField(default=list, blank=True)
    images = models.JSONField(default=list, blank=True)
    links = models.JSONField(default=dict, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-published"]
        verbose_name = "News Article"
        verbose_name_plural = "News Articles"

    def __str__(self) -> str:
        return self.headline[:80]

    @property
    def thumbnail(self) -> str | None:
        """Return thumbnail URL from first image entry."""
        for img in self.images:
            if isinstance(img, dict):
                return img.get("url") or img.get("href")
        return None


class Injury(TimestampMixin):
    """Player injury record from the league injuries endpoint."""

    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name="injuries")
    team = models.ForeignKey(
        Team, on_delete=models.SET_NULL, null=True, blank=True, related_name="injuries"
    )
    espn_id = models.CharField(max_length=100, blank=True, db_index=True)
    athlete_espn_id = models.CharField(max_length=50, blank=True, db_index=True)
    athlete_name = models.CharField(max_length=100)
    position = models.CharField(max_length=50, blank=True)

    STATUS_OUT = "out"
    STATUS_QUESTIONABLE = "questionable"
    STATUS_DOUBTFUL = "doubtful"
    STATUS_IR = "ir"
    STATUS_DAY_TO_DAY = "day_to_day"
    STATUS_OTHER = "other"
    STATUS_CHOICES = [
        ("out", "Out"),
        ("questionable", "Questionable"),
        ("doubtful", "Doubtful"),
        ("ir", "IR"),
        ("day_to_day", "Day-to-Day"),
        ("other", "Other"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="other", db_index=True)
    status_display = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=500, blank=True)
    injury_type = models.CharField(max_length=100, blank=True)
    injury_date = models.DateField(null=True, blank=True)
    return_date = models.DateField(null=True, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Injury"
        verbose_name_plural = "Injuries"

    def __str__(self) -> str:
        return f"{self.athlete_name} ({self.status_display or self.status})"


class Transaction(TimestampMixin):
    """Transaction record (signing, trade, waiver, release, etc.)."""

    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name="transactions")
    team = models.ForeignKey(
        Team, on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions"
    )
    espn_id = models.CharField(max_length=100, blank=True, db_index=True)
    date = models.DateField(null=True, blank=True, db_index=True)
    description = models.TextField()
    type = models.CharField(max_length=100, blank=True)
    athlete_name = models.CharField(max_length=100, blank=True)
    athlete_espn_id = models.CharField(max_length=50, blank=True, db_index=True)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-date", "-updated_at"]
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"

    def __str__(self) -> str:
        return self.description[:80]


class AthleteSeasonStats(TimestampMixin):
    """Athlete season statistics from common/v3 stats endpoint."""

    athlete = models.ForeignKey(
        Athlete, on_delete=models.CASCADE, related_name="season_stats", null=True, blank=True
    )
    league = models.ForeignKey(
        League, on_delete=models.CASCADE, related_name="athlete_season_stats"
    )
    athlete_espn_id = models.CharField(max_length=50, db_index=True)
    athlete_name = models.CharField(max_length=100, blank=True)
    season_year = models.PositiveIntegerField(db_index=True)
    season_type = models.PositiveSmallIntegerField(default=2)  # 2=regular, 3=postseason
    # Flexible stats JSON — structure varies by sport
    stats = models.JSONField(default=dict, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-season_year"]
        unique_together = [["league", "athlete_espn_id", "season_year", "season_type"]]
        verbose_name = "Athlete Season Stats"
        verbose_name_plural = "Athlete Season Stats"

    def __str__(self) -> str:
        return f"{self.athlete_name} — {self.league.slug.upper()} {self.season_year}"

```

---

# FILE: `espn_service/apps/espn/serializers.py`

```python
"""Serializers for ESPN data models."""

from rest_framework import serializers

from apps.espn.models import (
    Athlete,
    AthleteSeasonStats,
    Competitor,
    Event,
    Injury,
    League,
    NewsArticle,
    Sport,
    Team,
    Transaction,
    Venue,
)


class SportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sport
        fields = ["id", "slug", "name", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class LeagueSerializer(serializers.ModelSerializer):
    sport = SportSerializer(read_only=True)
    sport_slug = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = League
        fields = ["id", "slug", "name", "abbreviation", "sport", "sport_slug", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class LeagueMinimalSerializer(serializers.ModelSerializer):
    sport_slug = serializers.CharField(source="sport.slug", read_only=True)

    class Meta:
        model = League
        fields = ["id", "slug", "name", "abbreviation", "sport_slug"]


class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = [
            "id", "espn_id", "name", "city", "state", "country",
            "is_indoor", "capacity", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TeamSerializer(serializers.ModelSerializer):
    league = LeagueMinimalSerializer(read_only=True)
    primary_logo = serializers.CharField(read_only=True)

    class Meta:
        model = Team
        fields = [
            "id", "espn_id", "uid", "slug", "abbreviation", "display_name",
            "short_display_name", "name", "nickname", "location", "color",
            "alternate_color", "is_active", "is_all_star", "logos", "primary_logo",
            "league", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TeamListSerializer(serializers.ModelSerializer):
    league_slug = serializers.CharField(source="league.slug", read_only=True)
    sport_slug = serializers.CharField(source="league.sport.slug", read_only=True)
    primary_logo = serializers.CharField(read_only=True)

    class Meta:
        model = Team
        fields = [
            "id", "espn_id", "abbreviation", "display_name", "short_display_name",
            "location", "color", "primary_logo", "league_slug", "sport_slug", "is_active",
        ]


class TeamMinimalSerializer(serializers.ModelSerializer):
    primary_logo = serializers.CharField(read_only=True)

    class Meta:
        model = Team
        fields = [
            "id", "espn_id", "abbreviation", "display_name",
            "short_display_name", "location", "color", "primary_logo",
        ]


class CompetitorSerializer(serializers.ModelSerializer):
    team = TeamMinimalSerializer(read_only=True)
    score_int = serializers.IntegerField(read_only=True)

    class Meta:
        model = Competitor
        fields = [
            "id", "team", "home_away", "score", "score_int",
            "winner", "line_scores", "records", "statistics", "leaders", "order",
        ]


class EventSerializer(serializers.ModelSerializer):
    league = LeagueMinimalSerializer(read_only=True)
    venue = VenueSerializer(read_only=True)
    competitors = CompetitorSerializer(many=True, read_only=True)

    class Meta:
        model = Event
        fields = [
            "id", "espn_id", "uid", "date", "name", "short_name",
            "season_year", "season_type", "season_slug", "week",
            "status", "status_detail", "clock", "period", "attendance",
            "broadcasts", "links", "league", "venue", "competitors",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class EventListSerializer(serializers.ModelSerializer):
    league_slug = serializers.CharField(source="league.slug", read_only=True)
    sport_slug = serializers.CharField(source="league.sport.slug", read_only=True)
    venue_name = serializers.CharField(source="venue.name", read_only=True, allow_null=True)
    competitors = CompetitorSerializer(many=True, read_only=True)

    class Meta:
        model = Event
        fields = [
            "id", "espn_id", "date", "name", "short_name", "status", "status_detail",
            "league_slug", "sport_slug", "venue_name", "competitors",
        ]


class AthleteSerializer(serializers.ModelSerializer):
    team = TeamMinimalSerializer(read_only=True)

    class Meta:
        model = Athlete
        fields = [
            "id", "espn_id", "uid", "first_name", "last_name", "full_name",
            "display_name", "short_name", "position", "position_abbreviation",
            "jersey", "is_active", "height", "weight", "age", "birth_date",
            "birth_place", "headshot", "team", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# ---------------------------------------------------------------------------
# New model serializers — added in audit expansion
# ---------------------------------------------------------------------------


class NewsArticleSerializer(serializers.ModelSerializer):
    """Serializer for NewsArticle model."""

    league_slug = serializers.CharField(source="league.slug", read_only=True, allow_null=True)
    sport_slug = serializers.CharField(source="league.sport.slug", read_only=True, allow_null=True)
    thumbnail = serializers.CharField(read_only=True)

    class Meta:
        model = NewsArticle
        fields = [
            "id", "espn_id", "headline", "description", "published",
            "last_modified", "type", "categories", "images", "links",
            "thumbnail", "league_slug", "sport_slug", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class NewsArticleListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for news article lists."""

    league_slug = serializers.CharField(source="league.slug", read_only=True, allow_null=True)
    sport_slug = serializers.CharField(source="league.sport.slug", read_only=True, allow_null=True)
    thumbnail = serializers.CharField(read_only=True)

    class Meta:
        model = NewsArticle
        fields = [
            "id", "espn_id", "headline", "description", "published",
            "type", "thumbnail", "league_slug", "sport_slug",
        ]


class InjurySerializer(serializers.ModelSerializer):
    """Serializer for Injury model."""

    league_slug = serializers.CharField(source="league.slug", read_only=True)
    sport_slug = serializers.CharField(source="league.sport.slug", read_only=True)
    team_abbreviation = serializers.CharField(
        source="team.abbreviation", read_only=True, allow_null=True
    )

    class Meta:
        model = Injury
        fields = [
            "id", "athlete_espn_id", "athlete_name", "position",
            "status", "status_display", "description", "injury_type",
            "injury_date", "return_date",
            "league_slug", "sport_slug", "team_abbreviation",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for Transaction model."""

    league_slug = serializers.CharField(source="league.slug", read_only=True)
    sport_slug = serializers.CharField(source="league.sport.slug", read_only=True)
    team_abbreviation = serializers.CharField(
        source="team.abbreviation", read_only=True, allow_null=True
    )

    class Meta:
        model = Transaction
        fields = [
            "id", "espn_id", "date", "description", "type",
            "athlete_name", "athlete_espn_id",
            "league_slug", "sport_slug", "team_abbreviation",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AthleteSeasonStatsSerializer(serializers.ModelSerializer):
    """Serializer for AthleteSeasonStats model."""

    league_slug = serializers.CharField(source="league.slug", read_only=True)
    sport_slug = serializers.CharField(source="league.sport.slug", read_only=True)

    class Meta:
        model = AthleteSeasonStats
        fields = [
            "id", "athlete_espn_id", "athlete_name",
            "season_year", "season_type", "stats",
            "league_slug", "sport_slug",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

```

---

# FILE: `espn_service/apps/espn/urls.py`

```python
"""URL configuration for ESPN app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.espn.views import (
    AthleteSeasonStatsViewSet,
    EventViewSet,
    InjuryViewSet,
    LeagueViewSet,
    NewsArticleViewSet,
    SportViewSet,
    TeamViewSet,
    TransactionViewSet,
)

app_name = "espn"

router = DefaultRouter()
router.register(r"sports", SportViewSet, basename="sport")
router.register(r"leagues", LeagueViewSet, basename="league")
router.register(r"teams", TeamViewSet, basename="team")
router.register(r"events", EventViewSet, basename="event")
router.register(r"news", NewsArticleViewSet, basename="news")
router.register(r"injuries", InjuryViewSet, basename="injury")
router.register(r"transactions", TransactionViewSet, basename="transaction")
router.register(r"athlete-stats", AthleteSeasonStatsViewSet, basename="athlete-stats")

urlpatterns = [
    path("", include(router.urls)),
]

```

---

# FILE: `espn_service/apps/espn/views.py`

```python
"""Views for ESPN data API endpoints."""

from django.db.models import QuerySet
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.espn.filters import EventFilter, TeamFilter
from apps.espn.models import (
    AthleteSeasonStats,
    Event,
    Injury,
    League,
    NewsArticle,
    Sport,
    Team,
    Transaction,
)
from apps.espn.serializers import (
    AthleteSeasonStatsSerializer,
    EventListSerializer,
    EventSerializer,
    InjurySerializer,
    LeagueSerializer,
    NewsArticleListSerializer,
    NewsArticleSerializer,
    SportSerializer,
    TeamListSerializer,
    TeamSerializer,
    TransactionSerializer,
)


class SportViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Sport discovery."""

    serializer_class = SportSerializer
    lookup_field = "slug"

    def get_queryset(self) -> QuerySet[Sport]:
        return Sport.objects.prefetch_related("leagues").order_by("name")

    @extend_schema(tags=["Discovery"], summary="List sports")
    def list(self, request: Request, *args, **kwargs) -> Response:
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=["Discovery"], summary="Get sport details")
    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        return super().retrieve(request, *args, **kwargs)


class LeagueViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for League discovery."""

    serializer_class = LeagueSerializer

    def get_queryset(self) -> QuerySet[League]:
        qs = League.objects.select_related("sport").order_by("sport__name", "name")
        sport = self.request.query_params.get("sport")
        if sport:
            qs = qs.filter(sport__slug__iexact=sport)
        return qs

    @extend_schema(
        tags=["Discovery"],
        summary="List leagues",
        parameters=[OpenApiParameter("sport", description="Filter by sport slug", type=str)],
    )
    def list(self, request: Request, *args, **kwargs) -> Response:
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=["Discovery"], summary="Get league details")
    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        return super().retrieve(request, *args, **kwargs)


class TeamViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Team data."""

    filterset_class = TeamFilter
    search_fields = ["display_name", "abbreviation", "location", "name"]
    ordering_fields = ["display_name", "abbreviation", "created_at"]
    ordering = ["display_name"]

    def get_queryset(self) -> QuerySet[Team]:
        return Team.objects.select_related("league", "league__sport").filter(is_active=True)

    def get_serializer_class(self) -> type:
        if self.action == "list":
            return TeamListSerializer
        return TeamSerializer

    @extend_schema(
        tags=["Teams"],
        summary="List teams",
        parameters=[
            OpenApiParameter("sport", description="Filter by sport slug", type=str),
            OpenApiParameter("league", description="Filter by league slug", type=str),
            OpenApiParameter("search", description="Search in name/abbreviation/location", type=str),
        ],
    )
    def list(self, request: Request, *args, **kwargs) -> Response:
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=["Teams"], summary="Get team details")
    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        tags=["Teams"],
        summary="Get team by ESPN ID",
        parameters=[OpenApiParameter("espn_id", location=OpenApiParameter.PATH, type=str)],
    )
    @action(detail=False, methods=["get"], url_path="espn/(?P<espn_id>[^/.]+)")
    def by_espn_id(self, request: Request, espn_id: str) -> Response:  # noqa: ARG002
        team = self.get_queryset().filter(espn_id=espn_id).first()
        if not team:
            return Response({"error": "Team not found"}, status=404)
        return Response(TeamSerializer(team).data)


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Event/Game data."""

    filterset_class = EventFilter
    search_fields = ["name", "short_name"]
    ordering_fields = ["date", "created_at"]
    ordering = ["-date"]

    def get_queryset(self) -> QuerySet[Event]:
        return Event.objects.select_related(
            "league", "league__sport", "venue"
        ).prefetch_related("competitors", "competitors__team")

    def get_serializer_class(self) -> type:
        if self.action == "list":
            return EventListSerializer
        return EventSerializer

    @extend_schema(
        tags=["Events"],
        summary="List events",
        parameters=[
            OpenApiParameter("sport", description="Filter by sport slug", type=str),
            OpenApiParameter("league", description="Filter by league slug", type=str),
            OpenApiParameter("date", description="Filter by date (YYYY-MM-DD)", type=str),
            OpenApiParameter("date_from", description="Filter date >=", type=str),
            OpenApiParameter("date_to", description="Filter date <=", type=str),
            OpenApiParameter("status", description="Filter by status", type=str),
            OpenApiParameter("team", description="Filter by team ESPN ID or abbreviation", type=str),
        ],
    )
    def list(self, request: Request, *args, **kwargs) -> Response:
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=["Events"], summary="Get event details")
    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        tags=["Events"],
        summary="Get event by ESPN ID",
        parameters=[OpenApiParameter("espn_id", location=OpenApiParameter.PATH, type=str)],
    )
    @action(detail=False, methods=["get"], url_path="espn/(?P<espn_id>[^/.]+)")
    def by_espn_id(self, request: Request, espn_id: str) -> Response:  # noqa: ARG002
        event = self.get_queryset().filter(espn_id=espn_id).first()
        if not event:
            return Response({"error": "Event not found"}, status=404)
        return Response(EventSerializer(event).data)


# ---------------------------------------------------------------------------
# New ViewSets — added in audit expansion
# ---------------------------------------------------------------------------


class NewsArticleViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for ESPN news articles."""

    search_fields = ["headline", "description"]
    ordering_fields = ["published", "created_at"]
    ordering = ["-published"]

    def get_queryset(self) -> QuerySet[NewsArticle]:
        qs = NewsArticle.objects.select_related("league", "league__sport")

        sport = self.request.query_params.get("sport")
        if sport:
            qs = qs.filter(league__sport__slug__iexact=sport)

        league = self.request.query_params.get("league")
        if league:
            qs = qs.filter(league__slug__iexact=league)

        date_from = self.request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(published__date__gte=date_from)

        return qs

    def get_serializer_class(self) -> type:
        if self.action == "list":
            return NewsArticleListSerializer
        return NewsArticleSerializer

    @extend_schema(
        tags=["News"],
        summary="List news articles",
        parameters=[
            OpenApiParameter("sport", description="Filter by sport slug", type=str),
            OpenApiParameter("league", description="Filter by league slug", type=str),
            OpenApiParameter("date_from", description="Published on or after (YYYY-MM-DD)", type=str),
            OpenApiParameter("search", description="Search headline/description", type=str),
        ],
    )
    def list(self, request: Request, *args, **kwargs) -> Response:
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=["News"], summary="Get news article detail")
    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        return super().retrieve(request, *args, **kwargs)


class InjuryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for league injury reports."""

    serializer_class = InjurySerializer
    search_fields = ["athlete_name", "injury_type", "description"]
    ordering_fields = ["updated_at", "athlete_name"]
    ordering = ["-updated_at"]

    def get_queryset(self) -> QuerySet[Injury]:
        qs = Injury.objects.select_related("league", "league__sport", "team")

        sport = self.request.query_params.get("sport")
        if sport:
            qs = qs.filter(league__sport__slug__iexact=sport)

        league = self.request.query_params.get("league")
        if league:
            qs = qs.filter(league__slug__iexact=league)

        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status__iexact=status_param)

        team = self.request.query_params.get("team")
        if team:
            qs = qs.filter(team__abbreviation__iexact=team)

        return qs

    @extend_schema(
        tags=["Injuries"],
        summary="List injury reports",
        parameters=[
            OpenApiParameter("sport", description="Filter by sport slug", type=str),
            OpenApiParameter("league", description="Filter by league slug (e.g., 'nfl')", type=str),
            OpenApiParameter(
                "status",
                description="Filter by status (out, questionable, doubtful, ir, day_to_day)",
                type=str,
            ),
            OpenApiParameter("team", description="Filter by team abbreviation", type=str),
            OpenApiParameter("search", description="Search athlete name / injury type", type=str),
        ],
    )
    def list(self, request: Request, *args, **kwargs) -> Response:
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=["Injuries"], summary="Get injury detail")
    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        return super().retrieve(request, *args, **kwargs)


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for league transaction records."""

    serializer_class = TransactionSerializer
    search_fields = ["description", "athlete_name", "type"]
    ordering_fields = ["date", "created_at"]
    ordering = ["-date"]

    def get_queryset(self) -> QuerySet[Transaction]:
        qs = Transaction.objects.select_related("league", "league__sport", "team")

        sport = self.request.query_params.get("sport")
        if sport:
            qs = qs.filter(league__sport__slug__iexact=sport)

        league = self.request.query_params.get("league")
        if league:
            qs = qs.filter(league__slug__iexact=league)

        date_from = self.request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(date__gte=date_from)

        return qs

    @extend_schema(
        tags=["Transactions"],
        summary="List transactions",
        parameters=[
            OpenApiParameter("sport", description="Filter by sport slug", type=str),
            OpenApiParameter("league", description="Filter by league slug", type=str),
            OpenApiParameter("date_from", description="Transactions on or after (YYYY-MM-DD)", type=str),
            OpenApiParameter("search", description="Search description / athlete name / type", type=str),
        ],
    )
    def list(self, request: Request, *args, **kwargs) -> Response:
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=["Transactions"], summary="Get transaction detail")
    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        return super().retrieve(request, *args, **kwargs)


class AthleteSeasonStatsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for stored athlete season stats."""

    serializer_class = AthleteSeasonStatsSerializer
    search_fields = ["athlete_name"]
    ordering_fields = ["season_year", "athlete_name"]
    ordering = ["-season_year"]

    def get_queryset(self) -> QuerySet[AthleteSeasonStats]:
        qs = AthleteSeasonStats.objects.select_related("league", "league__sport", "athlete")

        sport = self.request.query_params.get("sport")
        if sport:
            qs = qs.filter(league__sport__slug__iexact=sport)

        league = self.request.query_params.get("league")
        if league:
            qs = qs.filter(league__slug__iexact=league)

        season = self.request.query_params.get("season")
        if season and season.isdigit():
            qs = qs.filter(season_year=int(season))

        athlete_id = self.request.query_params.get("athlete_espn_id")
        if athlete_id:
            qs = qs.filter(athlete_espn_id=athlete_id)

        return qs

    @extend_schema(
        tags=["Athlete Stats"],
        summary="List athlete season stats",
        parameters=[
            OpenApiParameter("sport", description="Filter by sport slug", type=str),
            OpenApiParameter("league", description="Filter by league slug", type=str),
            OpenApiParameter("season", description="Filter by season year (e.g., 2024)", type=int),
            OpenApiParameter("athlete_espn_id", description="Filter by ESPN athlete ID", type=str),
            OpenApiParameter("search", description="Search athlete name", type=str),
        ],
    )
    def list(self, request: Request, *args, **kwargs) -> Response:
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=["Athlete Stats"], summary="Get athlete season stats detail")
    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        return super().retrieve(request, *args, **kwargs)

```

---

# FILE: `espn_service/apps/ingest/__init__.py`

```python
# Ingest app

```

---

# FILE: `espn_service/apps/ingest/apps.py`

```python
"""Ingest app configuration."""

from django.apps import AppConfig


class IngestConfig(AppConfig):
    """Ingest application configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ingest"
    verbose_name = "Data Ingestion"

```

---

# FILE: `espn_service/apps/ingest/management/__init__.py`

```python
# Management commands package

```

---

# FILE: `espn_service/apps/ingest/management/commands/__init__.py`

```python
# Commands package

```

---

# FILE: `espn_service/apps/ingest/management/commands/ingest_all_teams.py`

```python
"""Management command to ingest teams for all configured leagues."""

from django.core.management.base import BaseCommand, CommandError

from apps.ingest.services import TeamIngestionService

# All major leagues across all 17 sports
ALL_LEAGUES = [
    # Football
    ("football", "nfl"),
    ("football", "college-football"),
    ("football", "cfl"),
    ("football", "ufl"),
    ("football", "xfl"),
    # Basketball
    ("basketball", "nba"),
    ("basketball", "wnba"),
    ("basketball", "mens-college-basketball"),
    ("basketball", "womens-college-basketball"),
    ("basketball", "nba-development"),
    ("basketball", "nbl"),
    # Baseball
    ("baseball", "mlb"),
    ("baseball", "college-baseball"),
    # Hockey
    ("hockey", "nhl"),
    ("hockey", "mens-college-hockey"),
    ("hockey", "womens-college-hockey"),
    # Soccer — top leagues + major competitions
    ("soccer", "eng.1"),
    ("soccer", "usa.1"),
    ("soccer", "esp.1"),
    ("soccer", "ger.1"),
    ("soccer", "ita.1"),
    ("soccer", "fra.1"),
    ("soccer", "mex.1"),
    ("soccer", "uefa.champions"),
    ("soccer", "uefa.europa"),
    ("soccer", "usa.nwsl"),
    ("soccer", "eng.2"),
    # MMA
    ("mma", "ufc"),
    ("mma", "bellator"),
    # Golf
    ("golf", "pga"),
    ("golf", "lpga"),
    ("golf", "liv"),
    ("golf", "eur"),
    # Tennis
    ("tennis", "atp"),
    ("tennis", "wta"),
    # Racing
    ("racing", "f1"),
    ("racing", "irl"),
    ("racing", "nascar-premier"),
    ("racing", "nascar-secondary"),
    ("racing", "nascar-truck"),
    # Rugby Union (numeric IDs)
    ("rugby", "164205"),   # Rugby World Cup
    ("rugby", "180659"),   # Six Nations
    ("rugby", "267979"),   # Gallagher Premiership
    ("rugby", "242041"),   # Super Rugby Pacific
    ("rugby", "289262"),   # Major League Rugby
    # Rugby League
    ("rugby-league", "3"),
    # Lacrosse
    ("lacrosse", "pll"),
    ("lacrosse", "nll"),
    ("lacrosse", "mens-college-lacrosse"),
    ("lacrosse", "womens-college-lacrosse"),
    # Australian Football
    ("australian-football", "afl"),
]


class Command(BaseCommand):
    """Django management command to ingest teams for all supported leagues."""

    help = (
        "Ingest team data from ESPN for all configured leagues. "
        "Use --sport to filter by sport or --dry-run to preview without ingesting."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--sport",
            type=str,
            default=None,
            help="Optional: filter to a single sport slug (e.g., basketball)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Print leagues that would be ingested without actually ingesting",
        )
        parser.add_argument(
            "--continue-on-error",
            action="store_true",
            default=True,
            help="Continue processing remaining leagues if one fails (default: True)",
        )

    def handle(self, *args, **options):
        sport_filter = options.get("sport")
        dry_run = options["dry_run"]
        continue_on_error = options["continue_on_error"]

        leagues = ALL_LEAGUES
        if sport_filter:
            leagues = [(s, league_slug) for s, league_slug in ALL_LEAGUES if s == sport_filter.lower()]
            if not leagues:
                raise CommandError(
                    f"No leagues configured for sport: {sport_filter}. "
                    f"Available sports: {sorted({s for s, _ in ALL_LEAGUES})}"
                )

        self.stdout.write(
            f"{'[DRY RUN] ' if dry_run else ''}Ingesting teams for "
            f"{len(leagues)} league(s)"
            + (f" (sport: {sport_filter})" if sport_filter else "")
        )

        if dry_run:
            for sport, league in leagues:
                self.stdout.write(f"  • {sport}/{league}")
            return

        total_created = 0
        total_updated = 0
        total_errors = 0
        failures = []

        for sport, league in leagues:
            self.stdout.write(f"  Ingesting {sport}/{league}...", ending="")

            try:
                service = TeamIngestionService()
                result = service.ingest_teams(sport, league)
                total_created += result.created
                total_updated += result.updated
                total_errors += result.errors

                status_str = (
                    self.style.SUCCESS(
                        f" ✓ created={result.created} updated={result.updated}"
                        + (f" errors={result.errors}" if result.errors else "")
                    )
                )
                self.stdout.write(status_str)

            except Exception as e:
                failure_msg = f" ✗ {e}"
                self.stdout.write(self.style.ERROR(failure_msg))
                failures.append(f"{sport}/{league}: {e}")
                if not continue_on_error:
                    raise CommandError(f"Stopped at {sport}/{league}: {e}") from e

        # Summary
        self.stdout.write("\n" + "─" * 50)
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Total: created={total_created} updated={total_updated} "
                f"errors={total_errors} failed_leagues={len(failures)}"
            )
        )
        if failures:
            self.stdout.write(self.style.WARNING("Failed leagues:"))
            for f in failures:
                self.stdout.write(self.style.WARNING(f"  • {f}"))

```

---

# FILE: `espn_service/apps/ingest/management/commands/ingest_injuries.py`

```python
"""Management command to ingest ESPN injury reports."""

import argparse

from django.core.management.base import BaseCommand, CommandError

from apps.ingest.services import InjuryIngestionService
from apps.ingest.tasks import ALL_LEAGUES_CONFIG


class Command(BaseCommand):
    help = "Refresh ESPN injury reports for one or all configured leagues."

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--sport", type=str, help="Sport slug (e.g., football)")
        parser.add_argument("--league", type=str, help="League slug (e.g., nfl)")

    def handle(self, *args, **options) -> None:  # noqa: ARG002
        sport = options.get("sport")
        league = options.get("league")

        if sport and league:
            leagues = [(sport.lower(), league.lower())]
        elif sport or league:
            raise CommandError("Provide both --sport and --league, or neither to run all leagues.")
        else:
            leagues = ALL_LEAGUES_CONFIG

        service = InjuryIngestionService()
        total_created = total_errors = 0

        for s, l in leagues:
            try:
                result = service.ingest_injuries(s, l)
                total_created += result.created
                total_errors += result.errors
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  [{s}/{l}] created={result.created} errors={result.errors}"
                    )
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  [{s}/{l}] FAILED: {e}"))
                total_errors += 1

        self.stdout.write(
            self.style.SUCCESS(f"\nDone — created={total_created} errors={total_errors}")
        )

```

---

# FILE: `espn_service/apps/ingest/management/commands/ingest_news.py`

```python
"""Management command to ingest ESPN news articles."""

import argparse

import structlog
from django.core.management.base import BaseCommand, CommandError

from apps.ingest.services import NewsIngestionService
from apps.ingest.tasks import ALL_LEAGUES_CONFIG

logger = structlog.get_logger(__name__)


class Command(BaseCommand):
    help = "Ingest ESPN news articles for one or all configured leagues."

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--sport", type=str, help="Sport slug (e.g., basketball)")
        parser.add_argument("--league", type=str, help="League slug (e.g., nba)")
        parser.add_argument(
            "--limit",
            type=int,
            default=50,
            help="Number of articles to fetch per league (default: 50)",
        )

    def handle(self, *args, **options) -> None:  # noqa: ARG002
        sport = options.get("sport")
        league = options.get("league")
        limit: int = options["limit"]

        if sport and league:
            leagues = [(sport.lower(), league.lower())]
        elif sport or league:
            raise CommandError("Provide both --sport and --league, or neither to run all leagues.")
        else:
            leagues = ALL_LEAGUES_CONFIG

        service = NewsIngestionService()
        total_created = total_updated = total_errors = 0

        for s, l in leagues:
            try:
                result = service.ingest_news(s, l, limit=limit)
                total_created += result.created
                total_updated += result.updated
                total_errors += result.errors
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  [{s}/{l}] created={result.created} updated={result.updated} errors={result.errors}"
                    )
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  [{s}/{l}] FAILED: {e}"))
                total_errors += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone — created={total_created} updated={total_updated} errors={total_errors}"
            )
        )

```

---

# FILE: `espn_service/apps/ingest/management/commands/ingest_scoreboard.py`

```python
"""Management command to ingest scoreboard data from ESPN."""

from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from apps.ingest.services import ScoreboardIngestionService


class Command(BaseCommand):
    """Django management command to ingest scoreboard data from ESPN."""

    help = "Ingest scoreboard/event data from ESPN for a given sport, league, and date"

    def add_arguments(self, parser):
        parser.add_argument(
            "sport",
            type=str,
            help="Sport slug (e.g., basketball, football)",
        )
        parser.add_argument(
            "league",
            type=str,
            help="League slug (e.g., nba, nfl)",
        )
        parser.add_argument(
            "--date",
            type=str,
            default=None,
            help="Date in YYYYMMDD format (default: today)",
        )

    def handle(self, *args, **options):
        sport = options["sport"].lower()
        league = options["league"].lower()
        date = options["date"]

        if date is None:
            date = datetime.now().strftime("%Y%m%d")

        self.stdout.write(f"Ingesting scoreboard for {sport}/{league} on {date}...")

        try:
            service = ScoreboardIngestionService()
            result = service.ingest_scoreboard(sport, league, date)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully ingested scoreboard:\n"
                    f"  Created: {result.created}\n"
                    f"  Updated: {result.updated}\n"
                    f"  Errors: {result.errors}\n"
                    f"  Total processed: {result.total_processed}"
                )
            )

        except Exception as e:
            raise CommandError(f"Failed to ingest scoreboard: {e}") from e

```

---

# FILE: `espn_service/apps/ingest/management/commands/ingest_teams.py`

```python
"""Management command to ingest teams from ESPN."""

from django.core.management.base import BaseCommand, CommandError

from apps.ingest.services import TeamIngestionService


class Command(BaseCommand):
    """Django management command to ingest teams from ESPN."""

    help = "Ingest team data from ESPN for a given sport and league"

    def add_arguments(self, parser):
        parser.add_argument(
            "sport",
            type=str,
            help="Sport slug (e.g., basketball, football)",
        )
        parser.add_argument(
            "league",
            type=str,
            help="League slug (e.g., nba, nfl)",
        )

    def handle(self, *args, **options):
        sport = options["sport"].lower()
        league = options["league"].lower()

        self.stdout.write(f"Ingesting teams for {sport}/{league}...")

        try:
            service = TeamIngestionService()
            result = service.ingest_teams(sport, league)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully ingested teams:\n"
                    f"  Created: {result.created}\n"
                    f"  Updated: {result.updated}\n"
                    f"  Errors: {result.errors}\n"
                    f"  Total processed: {result.total_processed}"
                )
            )

        except Exception as e:
            raise CommandError(f"Failed to ingest teams: {e}") from e

```

---

# FILE: `espn_service/apps/ingest/management/commands/ingest_transactions.py`

```python
"""Management command to ingest ESPN transactions."""

import argparse

from django.core.management.base import BaseCommand, CommandError

from apps.ingest.services import TransactionIngestionService
from apps.ingest.tasks import ALL_LEAGUES_CONFIG


class Command(BaseCommand):
    help = "Ingest ESPN transaction records for one or all configured leagues."

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--sport", type=str, help="Sport slug (e.g., basketball)")
        parser.add_argument("--league", type=str, help="League slug (e.g., nba)")

    def handle(self, *args, **options) -> None:  # noqa: ARG002
        sport = options.get("sport")
        league = options.get("league")

        if sport and league:
            leagues = [(sport.lower(), league.lower())]
        elif sport or league:
            raise CommandError("Provide both --sport and --league, or neither to run all leagues.")
        else:
            leagues = ALL_LEAGUES_CONFIG

        service = TransactionIngestionService()
        total_created = total_updated = total_errors = 0

        for s, l in leagues:
            try:
                result = service.ingest_transactions(s, l)
                total_created += result.created
                total_updated += result.updated
                total_errors += result.errors
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  [{s}/{l}] created={result.created} updated={result.updated} errors={result.errors}"
                    )
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  [{s}/{l}] FAILED: {e}"))
                total_errors += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone — created={total_created} updated={total_updated} errors={total_errors}"
            )
        )

```

---

# FILE: `espn_service/apps/ingest/serializers.py`

```python
"""Serializers for ingest API endpoints."""

from rest_framework import serializers


class IngestScoreboardRequestSerializer(serializers.Serializer):
    """Request serializer for scoreboard ingestion."""

    sport = serializers.CharField(max_length=50, help_text="Sport slug (e.g., 'basketball')")
    league = serializers.CharField(max_length=50, help_text="League slug (e.g., 'nba')")
    date = serializers.CharField(
        max_length=8,
        required=False,
        allow_blank=True,
        help_text="Date in YYYYMMDD format (optional, defaults to today)",
    )

    def validate_sport(self, value: str) -> str:
        return value.lower().strip()

    def validate_league(self, value: str) -> str:
        return value.lower().strip()

    def validate_date(self, value: str) -> str | None:
        if not value:
            return None
        value = value.strip()
        if len(value) != 8 or not value.isdigit():
            raise serializers.ValidationError("Date must be in YYYYMMDD format (e.g., '20241215')")
        return value


class IngestTeamsRequestSerializer(serializers.Serializer):
    """Request serializer for teams ingestion."""

    sport = serializers.CharField(max_length=50, help_text="Sport slug (e.g., 'basketball')")
    league = serializers.CharField(max_length=50, help_text="League slug (e.g., 'nba')")

    def validate_sport(self, value: str) -> str:
        return value.lower().strip()

    def validate_league(self, value: str) -> str:
        return value.lower().strip()


class IngestNewsRequestSerializer(serializers.Serializer):
    """Request serializer for news ingestion."""

    sport = serializers.CharField(max_length=50, help_text="Sport slug (e.g., 'basketball')")
    league = serializers.CharField(max_length=50, help_text="League slug (e.g., 'nba')")
    limit = serializers.IntegerField(
        default=50, min_value=1, max_value=200, help_text="Number of articles to fetch (default 50)"
    )

    def validate_sport(self, value: str) -> str:
        return value.lower().strip()

    def validate_league(self, value: str) -> str:
        return value.lower().strip()


class IngestInjuriesRequestSerializer(serializers.Serializer):
    """Request serializer for injury ingestion."""

    sport = serializers.CharField(max_length=50, help_text="Sport slug (e.g., 'football')")
    league = serializers.CharField(max_length=50, help_text="League slug (e.g., 'nfl')")

    def validate_sport(self, value: str) -> str:
        return value.lower().strip()

    def validate_league(self, value: str) -> str:
        return value.lower().strip()


class IngestTransactionsRequestSerializer(serializers.Serializer):
    """Request serializer for transaction ingestion."""

    sport = serializers.CharField(max_length=50, help_text="Sport slug (e.g., 'basketball')")
    league = serializers.CharField(max_length=50, help_text="League slug (e.g., 'nba')")

    def validate_sport(self, value: str) -> str:
        return value.lower().strip()

    def validate_league(self, value: str) -> str:
        return value.lower().strip()


class IngestionResultSerializer(serializers.Serializer):
    """Serializer for ingestion results."""

    created = serializers.IntegerField(help_text="Number of new records created")
    updated = serializers.IntegerField(help_text="Number of existing records updated")
    errors = serializers.IntegerField(help_text="Number of records that failed to process")
    total_processed = serializers.IntegerField(help_text="Total records processed (created + updated)")
    details = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_null=True,
        help_text="Optional details about the ingestion",
    )

```

---

# FILE: `espn_service/apps/ingest/services.py`

```python
"""Data ingestion services for ESPN data.

This module contains services that orchestrate fetching data from ESPN
and persisting it to the database using idempotent upserts.
"""

from dataclasses import dataclass
from datetime import date as date_cls
from datetime import datetime
from typing import Any

import structlog
from django.db import transaction

from apps.core.exceptions import IngestionError
from apps.espn.models import Competitor, Event, League, Sport, Team, Venue
from clients.espn_client import ESPNClient, get_espn_client

logger = structlog.get_logger(__name__)


@dataclass
class IngestionResult:
    """Result of an ingestion operation."""

    created: int = 0
    updated: int = 0
    errors: int = 0
    details: list[str] | None = None

    @property
    def total_processed(self) -> int:
        return self.created + self.updated

    def to_dict(self) -> dict[str, Any]:
        return {
            "created": self.created,
            "updated": self.updated,
            "errors": self.errors,
            "total_processed": self.total_processed,
            "details": self.details,
        }


def get_or_create_sport_and_league(sport_slug: str, league_slug: str) -> tuple[Sport, League]:
    """Get or create Sport and League records."""
    from clients.espn_client import LEAGUE_INFO, SPORT_NAMES

    sport, _ = Sport.objects.get_or_create(
        slug=sport_slug,
        defaults={"name": SPORT_NAMES.get(sport_slug, sport_slug.replace("-", " ").title())},
    )

    league_name, league_abbr = LEAGUE_INFO.get(
        league_slug, (league_slug.replace("-", " ").title(), league_slug.upper()[:10])
    )
    league, _ = League.objects.get_or_create(
        sport=sport,
        slug=league_slug,
        defaults={
            "name": league_name,
            "abbreviation": league_abbr,
        },
    )

    return sport, league


class TeamIngestionService:
    """Service for ingesting team data from ESPN."""

    def __init__(self, client: ESPNClient | None = None):
        self.client = client or get_espn_client()

    def _parse_team_data(self, team_data: dict[str, Any]) -> dict[str, Any]:
        team_info = team_data.get("team", team_data)
        return {
            "espn_id": str(team_info.get("id", "")),
            "uid": team_info.get("uid", ""),
            "slug": team_info.get("slug", ""),
            "abbreviation": team_info.get("abbreviation", ""),
            "display_name": team_info.get("displayName", ""),
            "short_display_name": team_info.get("shortDisplayName", ""),
            "name": team_info.get("name", ""),
            "nickname": team_info.get("nickname", ""),
            "location": team_info.get("location", ""),
            "color": team_info.get("color", ""),
            "alternate_color": team_info.get("alternateColor", ""),
            "is_active": team_info.get("isActive", True),
            "is_all_star": team_info.get("isAllStar", False),
            "logos": team_info.get("logos", []),
            "links": team_info.get("links", []),
            "raw_data": team_info,
        }

    @transaction.atomic
    def ingest_teams(self, sport: str, league: str) -> IngestionResult:
        """Ingest all teams for a sport and league."""
        result = IngestionResult(details=[])

        try:
            _, league_obj = get_or_create_sport_and_league(sport, league)

            response = self.client.get_teams(sport, league)
            teams_data = response.data.get("sports", [{}])[0].get("leagues", [{}])[0].get(
                "teams", []
            )

            if not teams_data:
                logger.warning("no_teams_found", sport=sport, league=league)
                return result

            for team_data in teams_data:
                try:
                    parsed = self._parse_team_data(team_data)
                    espn_id = parsed.pop("espn_id")

                    if not espn_id:
                        result.errors += 1
                        continue

                    _, created = Team.objects.update_or_create(
                        league=league_obj,
                        espn_id=espn_id,
                        defaults=parsed,
                    )

                    if created:
                        result.created += 1
                    else:
                        result.updated += 1

                except Exception as e:
                    logger.error("team_ingestion_error", team_data=team_data, error=str(e))
                    result.errors += 1

            logger.info(
                "teams_ingested",
                sport=sport,
                league=league,
                created=result.created,
                updated=result.updated,
                errors=result.errors,
            )

        except Exception as e:
            logger.exception("team_ingestion_failed", sport=sport, league=league)
            raise IngestionError(f"Failed to ingest teams: {e}") from e

        return result


class ScoreboardIngestionService:
    """Service for ingesting scoreboard/event data from ESPN."""

    def __init__(self, client: ESPNClient | None = None):
        self.client = client or get_espn_client()

    def _parse_venue_data(self, venue_data: dict[str, Any]) -> dict[str, Any] | None:
        if not venue_data or not venue_data.get("id"):
            return None

        address = venue_data.get("address", {})
        return {
            "espn_id": str(venue_data.get("id", "")),
            "name": venue_data.get("fullName", venue_data.get("shortName", "")),
            "city": address.get("city", ""),
            "state": address.get("state", ""),
            "country": address.get("country", "USA"),
            "is_indoor": venue_data.get("indoor", True),
            "capacity": venue_data.get("capacity"),
            "raw_data": venue_data,
        }

    def _parse_event_status(self, status_data: dict[str, Any]) -> tuple[str, str]:
        type_data = status_data.get("type", {})
        state = type_data.get("state", "pre")
        completed = type_data.get("completed", False)

        if completed:
            return Event.STATUS_FINAL, type_data.get("detail", "Final")

        status_map = {
            "pre": Event.STATUS_SCHEDULED,
            "in": Event.STATUS_IN_PROGRESS,
            "post": Event.STATUS_FINAL,
        }
        return status_map.get(state, Event.STATUS_SCHEDULED), type_data.get("detail", "")

    def _parse_event_data(
        self, event_data: dict[str, Any], league: League  # noqa: ARG002
    ) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any] | None]:
        competitions = event_data.get("competitions", [])
        competition = competitions[0] if competitions else {}

        status_data = event_data.get("status", {})
        status, status_detail = self._parse_event_status(status_data)

        season_data = event_data.get("season", {})

        date_str = event_data.get("date", "")
        try:
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            date = datetime.now()

        event_fields = {
            "espn_id": str(event_data.get("id", "")),
            "uid": event_data.get("uid", ""),
            "date": date,
            "name": event_data.get("name", ""),
            "short_name": event_data.get("shortName", ""),
            "season_year": season_data.get("year", date.year),
            "season_type": season_data.get("type", 2),
            "season_slug": season_data.get("slug", ""),
            "week": event_data.get("week", {}).get("number"),
            "status": status,
            "status_detail": status_detail,
            "clock": status_data.get("displayClock", ""),
            "period": status_data.get("period"),
            "attendance": competition.get("attendance"),
            "broadcasts": competition.get("broadcasts", []),
            "links": event_data.get("links", []),
            "raw_data": event_data,
        }

        venue_data = self._parse_venue_data(competition.get("venue", {}))
        competitors_data = competition.get("competitors", [])

        return event_fields, competitors_data, venue_data

    def _get_or_create_venue(self, venue_data: dict[str, Any] | None) -> Venue | None:
        if not venue_data:
            return None
        espn_id = venue_data.pop("espn_id")
        venue, _ = Venue.objects.update_or_create(espn_id=espn_id, defaults=venue_data)
        return venue

    def _create_competitors(
        self,
        event: Event,
        competitors_data: list[dict[str, Any]],
        league: League,
    ) -> int:
        count = 0
        for idx, comp_data in enumerate(competitors_data):
            team_data = comp_data.get("team", {})
            team_id = str(team_data.get("id", ""))

            if not team_id:
                continue

            try:
                team = Team.objects.get(league=league, espn_id=team_id)
            except Team.DoesNotExist:
                team = Team.objects.create(
                    league=league,
                    espn_id=team_id,
                    abbreviation=team_data.get("abbreviation", ""),
                    display_name=team_data.get("displayName", team_data.get("name", "")),
                    short_display_name=team_data.get("shortDisplayName", ""),
                    name=team_data.get("name", ""),
                    location=team_data.get("location", ""),
                    logos=team_data.get("logo", []),
                )

            home_away = comp_data.get("homeAway", "away")
            if home_away not in [Competitor.HOME, Competitor.AWAY]:
                home_away = Competitor.HOME if idx == 1 else Competitor.AWAY

            Competitor.objects.update_or_create(
                event=event,
                team=team,
                defaults={
                    "home_away": home_away,
                    "score": comp_data.get("score", ""),
                    "winner": comp_data.get("winner"),
                    "line_scores": comp_data.get("linescores", []),
                    "records": comp_data.get("records", []),
                    "statistics": comp_data.get("statistics", []),
                    "leaders": comp_data.get("leaders", []),
                    "order": idx,
                    "raw_data": comp_data,
                },
            )
            count += 1

        return count

    @transaction.atomic
    def ingest_scoreboard(
        self,
        sport: str,
        league: str,
        date: str | None = None,
    ) -> IngestionResult:
        """Ingest scoreboard data for a sport, league, and date."""
        result = IngestionResult(details=[])

        try:
            _, league_obj = get_or_create_sport_and_league(sport, league)

            response = self.client.get_scoreboard(sport, league, date)
            events_data = response.data.get("events", [])

            if not events_data:
                logger.info("no_events_found", sport=sport, league=league, date=date)
                return result

            for event_data in events_data:
                try:
                    event_fields, competitors_data, venue_data = self._parse_event_data(
                        event_data, league_obj
                    )

                    espn_id = event_fields.pop("espn_id")
                    if not espn_id:
                        result.errors += 1
                        continue

                    venue = self._get_or_create_venue(venue_data)

                    event, created = Event.objects.update_or_create(
                        league=league_obj,
                        espn_id=espn_id,
                        defaults={**event_fields, "venue": venue},
                    )

                    event.competitors.all().delete()
                    self._create_competitors(event, competitors_data, league_obj)

                    if created:
                        result.created += 1
                    else:
                        result.updated += 1

                except Exception as e:
                    logger.error("event_ingestion_error", event_id=event_data.get("id"), error=str(e))
                    result.errors += 1

            logger.info(
                "scoreboard_ingested",
                sport=sport,
                league=league,
                date=date,
                created=result.created,
                updated=result.updated,
                errors=result.errors,
            )

        except Exception as e:
            logger.exception("scoreboard_ingestion_failed", sport=sport, league=league, date=date)
            raise IngestionError(f"Failed to ingest scoreboard: {e}") from e

        return result


# ---------------------------------------------------------------------------
# New ingestion services — added in audit expansion
# ---------------------------------------------------------------------------


class NewsIngestionService:
    """Service for ingesting news articles from ESPN site API."""

    def __init__(self, client: ESPNClient | None = None):
        self.client = client or get_espn_client()

    def _parse_article(self, item: dict[str, Any]) -> dict[str, Any] | None:
        espn_id = str(item.get("dataSourceIdentifier") or item.get("id") or "")
        headline = item.get("headline") or item.get("title") or ""
        if not espn_id or not headline:
            return None

        def _parse_dt(s: str) -> datetime | None:
            try:
                return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None
            except (ValueError, AttributeError):
                return None

        return {
            "espn_id": espn_id,
            "headline": headline[:500],
            "description": item.get("description") or item.get("abstract") or "",
            "story": item.get("story") or "",
            "published": _parse_dt(item.get("published") or ""),
            "last_modified": _parse_dt(item.get("lastModified") or ""),
            "type": str(item.get("type") or ""),
            "categories": item.get("categories") or [],
            "images": item.get("images") or [],
            "links": item.get("links") or {},
            "raw_data": item,
        }

    @transaction.atomic
    def ingest_news(self, sport: str, league: str, limit: int = 50) -> IngestionResult:
        """Ingest news articles for a sport/league."""
        from apps.espn.models import NewsArticle

        result = IngestionResult(details=[])

        try:
            _, league_obj = get_or_create_sport_and_league(sport, league)

            response = self.client.get_news(sport, league, limit=limit)
            articles_data = response.data.get("articles", [])

            if not articles_data:
                logger.info("no_news_found", sport=sport, league=league)
                return result

            for raw_item in articles_data:
                try:
                    parsed = self._parse_article(raw_item)
                    if not parsed:
                        result.errors += 1
                        continue

                    espn_id = parsed.pop("espn_id")
                    _, created = NewsArticle.objects.update_or_create(
                        espn_id=espn_id,
                        defaults={**parsed, "league": league_obj},
                    )
                    if created:
                        result.created += 1
                    else:
                        result.updated += 1

                except Exception as e:
                    logger.error("news_article_error", error=str(e))
                    result.errors += 1

            logger.info(
                "news_ingested",
                sport=sport,
                league=league,
                created=result.created,
                updated=result.updated,
            )

        except Exception as e:
            logger.exception("news_ingestion_failed", sport=sport, league=league)
            raise IngestionError(f"Failed to ingest news: {e}") from e

        return result


class InjuryIngestionService:
    """Service for ingesting league injury reports from ESPN site API."""

    def __init__(self, client: ESPNClient | None = None):
        self.client = client or get_espn_client()

    _STATUS_MAP: dict[str, str] = {
        "out": "out",
        "doubtful": "doubtful",
        "questionable": "questionable",
        "injured reserve": "ir",
        "ir": "ir",
        "day-to-day": "day_to_day",
        "probable": "day_to_day",
    }

    def _normalize_status(self, raw: str) -> str:
        return self._STATUS_MAP.get(raw.lower().strip(), "other")

    def _parse_injury(self, item: dict[str, Any]) -> dict[str, Any] | None:
        athlete_data = item.get("athlete") or {}
        athlete_name = athlete_data.get("displayName") or athlete_data.get("fullName") or ""
        if not athlete_name:
            return None

        raw_status = item.get("status") or ""
        team_data = item.get("team") or {}

        return {
            "athlete_espn_id": str(athlete_data.get("id") or ""),
            "athlete_name": athlete_name,
            "position": (athlete_data.get("position") or {}).get("abbreviation") or "",
            "status": self._normalize_status(raw_status),
            "status_display": raw_status,
            "description": item.get("description") or item.get("shortComment") or "",
            "injury_type": item.get("type") or "",
            "team_espn_id": str(team_data.get("id") or ""),
            "raw_data": item,
        }

    @transaction.atomic
    def ingest_injuries(self, sport: str, league: str) -> IngestionResult:
        """Clear and re-ingest all league injuries (snapshot refresh)."""
        from apps.espn.models import Injury

        result = IngestionResult(details=[])

        try:
            _, league_obj = get_or_create_sport_and_league(sport, league)

            response = self.client.get_league_injuries(sport, league)
            items = response.data.get("items") or response.data.get("injuries") or []

            if not items:
                logger.info("no_injuries_found", sport=sport, league=league)
                return result

            # Injuries are a snapshot — delete stale entries then re-insert
            deleted, _ = Injury.objects.filter(league=league_obj).delete()
            logger.debug("cleared_old_injuries", count=deleted, sport=sport, league=league)

            for raw_item in items:
                try:
                    parsed = self._parse_injury(raw_item)
                    if not parsed:
                        result.errors += 1
                        continue

                    team_espn_id = parsed.pop("team_espn_id", "")
                    team_obj = (
                        Team.objects.filter(league=league_obj, espn_id=team_espn_id).first()
                        if team_espn_id
                        else None
                    )

                    Injury.objects.create(league=league_obj, team=team_obj, **parsed)
                    result.created += 1

                except Exception as e:
                    logger.error("injury_ingestion_error", error=str(e))
                    result.errors += 1

            logger.info(
                "injuries_ingested",
                sport=sport,
                league=league,
                created=result.created,
                errors=result.errors,
            )

        except Exception as e:
            logger.exception("injury_ingestion_failed", sport=sport, league=league)
            raise IngestionError(f"Failed to ingest injuries: {e}") from e

        return result


class TransactionIngestionService:
    """Service for ingesting league transactions from ESPN site API."""

    def __init__(self, client: ESPNClient | None = None):
        self.client = client or get_espn_client()

    def _parse_transaction(self, item: dict[str, Any]) -> dict[str, Any] | None:
        description = item.get("description") or item.get("text") or ""
        if not description:
            return None

        raw_date = item.get("date") or ""
        txn_date: date_cls | None = None
        try:
            if raw_date:
                txn_date = date_cls.fromisoformat(raw_date[:10])
        except (ValueError, TypeError):
            pass

        athlete_data = item.get("athlete") or {}
        team_data = item.get("team") or {}

        return {
            "espn_id": str(item.get("id") or ""),
            "date": txn_date,
            "description": description,
            "type": item.get("type") or "",
            "athlete_name": athlete_data.get("displayName") or "",
            "athlete_espn_id": str(athlete_data.get("id") or ""),
            "team_espn_id": str(team_data.get("id") or ""),
            "raw_data": item,
        }

    @transaction.atomic
    def ingest_transactions(self, sport: str, league: str) -> IngestionResult:
        """Ingest recent transactions for a sport/league."""
        from apps.espn.models import Transaction

        result = IngestionResult(details=[])

        try:
            _, league_obj = get_or_create_sport_and_league(sport, league)

            response = self.client.get_league_transactions(sport, league)
            items = response.data.get("items") or response.data.get("transactions") or []

            if not items:
                logger.info("no_transactions_found", sport=sport, league=league)
                return result

            for raw_item in items:
                try:
                    parsed = self._parse_transaction(raw_item)
                    if not parsed:
                        result.errors += 1
                        continue

                    team_espn_id = parsed.pop("team_espn_id", "")
                    team_obj = (
                        Team.objects.filter(league=league_obj, espn_id=team_espn_id).first()
                        if team_espn_id
                        else None
                    )

                    espn_id = parsed.get("espn_id") or ""
                    if espn_id:
                        _, created = Transaction.objects.update_or_create(
                            league=league_obj,
                            espn_id=espn_id,
                            defaults={**parsed, "team": team_obj},
                        )
                    else:
                        Transaction.objects.create(league=league_obj, team=team_obj, **parsed)
                        created = True

                    if created:
                        result.created += 1
                    else:
                        result.updated += 1

                except Exception as e:
                    logger.error("transaction_ingestion_error", error=str(e))
                    result.errors += 1

            logger.info(
                "transactions_ingested",
                sport=sport,
                league=league,
                created=result.created,
                updated=result.updated,
                errors=result.errors,
            )

        except Exception as e:
            logger.exception("transactions_ingestion_failed", sport=sport, league=league)
            raise IngestionError(f"Failed to ingest transactions: {e}") from e

        return result


class AthleteStatsIngestionService:
    """Service for ingesting athlete season stats from common/v3 endpoint."""

    def __init__(self, client: ESPNClient | None = None):
        self.client = client or get_espn_client()

    @transaction.atomic
    def ingest_athlete_stats(
        self,
        sport: str,
        league: str,
        athlete_espn_id: str | int,
        season: int | None = None,
        season_type: int = 2,
    ) -> IngestionResult:
        """Ingest season stats for a single athlete."""
        from apps.espn.models import Athlete, AthleteSeasonStats

        result = IngestionResult(details=[])

        try:
            _, league_obj = get_or_create_sport_and_league(sport, league)

            response = self.client.get_athlete_stats(
                sport, league, int(athlete_espn_id), season=season, season_type=season_type
            )
            data = response.data

            athlete_obj = Athlete.objects.filter(espn_id=str(athlete_espn_id)).first()
            athlete_name = athlete_obj.display_name if athlete_obj else str(athlete_espn_id)
            season_val = season or (data.get("season") or {}).get("year") or 0

            _, created = AthleteSeasonStats.objects.update_or_create(
                league=league_obj,
                athlete_espn_id=str(athlete_espn_id),
                season_year=season_val,
                season_type=season_type,
                defaults={
                    "athlete": athlete_obj,
                    "athlete_name": athlete_name,
                    "stats": data.get("stats") or data.get("splits") or {},
                    "raw_data": data,
                },
            )

            if created:
                result.created += 1
            else:
                result.updated += 1

            logger.info(
                "athlete_stats_ingested",
                sport=sport,
                league=league,
                athlete_espn_id=athlete_espn_id,
                season=season_val,
            )

        except Exception as e:
            logger.exception(
                "athlete_stats_ingestion_failed",
                sport=sport,
                league=league,
                athlete_espn_id=athlete_espn_id,
            )
            raise IngestionError(f"Failed to ingest athlete stats: {e}") from e

        return result

```

---

# FILE: `espn_service/apps/ingest/tasks.py`

```python
"""Celery tasks for ESPN data ingestion.

All tasks are idempotent — safe to retry or run concurrently for
different sport/league combinations.
"""

from __future__ import annotations

import structlog
from celery import shared_task

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# League configuration — keep in sync with ingest_all_teams.py
# ---------------------------------------------------------------------------

ALL_LEAGUES_CONFIG: list[tuple[str, str]] = [
    # Football
    ("football", "nfl"),
    ("football", "college-football"),
    ("football", "cfl"),
    ("football", "ufl"),
    ("football", "xfl"),
    # Basketball
    ("basketball", "nba"),
    ("basketball", "wnba"),
    ("basketball", "nba-development"),
    ("basketball", "mens-college-basketball"),
    ("basketball", "womens-college-basketball"),
    ("basketball", "nbl"),
    # Baseball
    ("baseball", "mlb"),
    ("baseball", "college-baseball"),
    # Hockey
    ("hockey", "nhl"),
    ("hockey", "mens-college-hockey"),
    ("hockey", "womens-college-hockey"),
    # Soccer — major leagues only for Celery (performance)
    ("soccer", "eng.1"),
    ("soccer", "esp.1"),
    ("soccer", "ger.1"),
    ("soccer", "ita.1"),
    ("soccer", "fra.1"),
    ("soccer", "usa.1"),
    ("soccer", "eng.2"),
    ("soccer", "uefa.champions"),
    # Golf
    ("golf", "pga"),
    ("golf", "lpga"),
    ("golf", "eur"),
    ("golf", "liv"),
    # Racing
    ("racing", "f1"),
    ("racing", "irl"),
    ("racing", "nascar-premier"),
    ("racing", "nascar-secondary"),
    ("racing", "nascar-truck"),
    # Tennis
    ("tennis", "atp"),
    ("tennis", "wta"),
    # MMA
    ("mma", "ufc"),
    ("mma", "bellator"),
    # Rugby
    ("rugby", "premiership"),
    ("rugby", "rugby-union-super-rugby"),
    ("rugby", "internationals"),
    # Rugby League
    ("rugby-league", "nrl"),
    # Lacrosse
    ("lacrosse", "pll"),
    ("lacrosse", "nll"),
    ("lacrosse", "mens-college-lacrosse"),
    ("lacrosse", "womens-college-lacrosse"),
]


# ---------------------------------------------------------------------------
# Scoreboard tasks
# ---------------------------------------------------------------------------


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def refresh_scoreboard_task(self, sport: str, league: str, date: str | None = None) -> dict:
    """Ingest scoreboard data for a single sport/league."""
    from apps.ingest.services import ScoreboardIngestionService

    try:
        service = ScoreboardIngestionService()
        result = service.ingest_scoreboard(sport, league, date)
        logger.info(
            "scoreboard_task_completed",
            sport=sport,
            league=league,
            date=date,
            created=result.created,
            updated=result.updated,
        )
        return result.to_dict()
    except Exception as exc:
        logger.error("scoreboard_task_failed", sport=sport, league=league, error=str(exc))
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def refresh_all_scoreboards_task(self) -> dict:
    """Ingest today's scoreboard for every configured league."""
    total = {"created": 0, "updated": 0, "errors": 0}
    for sport, league in ALL_LEAGUES_CONFIG:
        try:
            refresh_scoreboard_task.delay(sport, league)
        except Exception as e:
            logger.error("refresh_all_scoreboards_dispatch_error", sport=sport, league=league, error=str(e))
            total["errors"] += 1
    return total


# ---------------------------------------------------------------------------
# Team tasks
# ---------------------------------------------------------------------------


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def refresh_teams_task(self, sport: str, league: str) -> dict:
    """Ingest team data for a single sport/league."""
    from apps.ingest.services import TeamIngestionService

    try:
        service = TeamIngestionService()
        result = service.ingest_teams(sport, league)
        logger.info("teams_task_completed", sport=sport, league=league, created=result.created)
        return result.to_dict()
    except Exception as exc:
        logger.error("teams_task_failed", sport=sport, league=league, error=str(exc))
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def refresh_all_teams_task(self) -> dict:
    """Ingest teams for every configured league (weekly refresh)."""
    total = {"created": 0, "updated": 0, "errors": 0}
    for sport, league in ALL_LEAGUES_CONFIG:
        try:
            refresh_teams_task.delay(sport, league)
        except Exception as e:
            logger.error("refresh_all_teams_dispatch_error", sport=sport, league=league, error=str(e))
            total["errors"] += 1
    return total


# ---------------------------------------------------------------------------
# News tasks (NEW)
# ---------------------------------------------------------------------------


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def refresh_news_task(self, sport: str, league: str, limit: int = 50) -> dict:
    """Ingest news articles for a single sport/league."""
    from apps.ingest.services import NewsIngestionService

    try:
        service = NewsIngestionService()
        result = service.ingest_news(sport, league, limit=limit)
        logger.info(
            "news_task_completed",
            sport=sport,
            league=league,
            created=result.created,
            updated=result.updated,
        )
        return result.to_dict()
    except Exception as exc:
        logger.error("news_task_failed", sport=sport, league=league, error=str(exc))
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def refresh_all_news_task(self) -> dict:
    """Ingest latest news for every configured league (runs every 30 min)."""
    total = {"created": 0, "updated": 0, "errors": 0}
    for sport, league in ALL_LEAGUES_CONFIG:
        try:
            refresh_news_task.delay(sport, league)
        except Exception as e:
            logger.error("refresh_all_news_dispatch_error", sport=sport, league=league, error=str(e))
            total["errors"] += 1
    return total


# ---------------------------------------------------------------------------
# Injury tasks (NEW)
# ---------------------------------------------------------------------------


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def refresh_injuries_task(self, sport: str, league: str) -> dict:
    """Refresh injury report for a single sport/league (full snapshot)."""
    from apps.ingest.services import InjuryIngestionService

    try:
        service = InjuryIngestionService()
        result = service.ingest_injuries(sport, league)
        logger.info(
            "injuries_task_completed",
            sport=sport,
            league=league,
            created=result.created,
        )
        return result.to_dict()
    except Exception as exc:
        logger.error("injuries_task_failed", sport=sport, league=league, error=str(exc))
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def refresh_all_injuries_task(self) -> dict:
    """Refresh injury reports for every configured league (runs every 4 hours)."""
    total = {"created": 0, "errors": 0}
    for sport, league in ALL_LEAGUES_CONFIG:
        try:
            refresh_injuries_task.delay(sport, league)
        except Exception as e:
            logger.error("refresh_all_injuries_dispatch_error", sport=sport, league=league, error=str(e))
            total["errors"] += 1
    return total


# ---------------------------------------------------------------------------
# Transaction tasks (NEW)
# ---------------------------------------------------------------------------


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def refresh_transactions_task(self, sport: str, league: str) -> dict:
    """Ingest transactions for a single sport/league."""
    from apps.ingest.services import TransactionIngestionService

    try:
        service = TransactionIngestionService()
        result = service.ingest_transactions(sport, league)
        logger.info(
            "transactions_task_completed",
            sport=sport,
            league=league,
            created=result.created,
            updated=result.updated,
        )
        return result.to_dict()
    except Exception as exc:
        logger.error("transactions_task_failed", sport=sport, league=league, error=str(exc))
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def refresh_all_transactions_task(self) -> dict:
    """Refresh transaction feeds for every configured league (runs every 6 hours)."""
    total = {"created": 0, "updated": 0, "errors": 0}
    for sport, league in ALL_LEAGUES_CONFIG:
        try:
            refresh_transactions_task.delay(sport, league)
        except Exception as e:
            logger.error(
                "refresh_all_transactions_dispatch_error",
                sport=sport,
                league=league,
                error=str(e),
            )
            total["errors"] += 1
    return total

```

---

# FILE: `espn_service/apps/ingest/urls.py`

```python
"""URL configuration for ingest app."""

from django.urls import path

from apps.ingest.views import (
    IngestInjuriesView,
    IngestNewsView,
    IngestScoreboardView,
    IngestTeamsView,
    IngestTransactionsView,
)

app_name = "ingest"

urlpatterns = [
    path("scoreboard/", IngestScoreboardView.as_view(), name="ingest-scoreboard"),
    path("teams/", IngestTeamsView.as_view(), name="ingest-teams"),
    path("news/", IngestNewsView.as_view(), name="ingest-news"),
    path("injuries/", IngestInjuriesView.as_view(), name="ingest-injuries"),
    path("transactions/", IngestTransactionsView.as_view(), name="ingest-transactions"),
]

```

---

# FILE: `espn_service/apps/ingest/views.py`

```python
"""Views for ingestion API endpoints."""

import structlog
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ingest.serializers import (
    IngestionResultSerializer,
    IngestInjuriesRequestSerializer,
    IngestNewsRequestSerializer,
    IngestScoreboardRequestSerializer,
    IngestTeamsRequestSerializer,
    IngestTransactionsRequestSerializer,
)
from apps.ingest.services import (
    InjuryIngestionService,
    NewsIngestionService,
    ScoreboardIngestionService,
    TeamIngestionService,
    TransactionIngestionService,
)

logger = structlog.get_logger(__name__)


class IngestScoreboardView(APIView):
    """Endpoint for ingesting scoreboard data from ESPN."""

    @extend_schema(
        tags=["Ingest"],
        summary="Ingest scoreboard data",
        description=(
            "Fetch scoreboard data from ESPN for a specific sport, league, and date, "
            "then upsert the events and competitors into the database."
        ),
        request=IngestScoreboardRequestSerializer,
        responses={
            200: IngestionResultSerializer,
            400: {"description": "Invalid request data"},
            502: {"description": "ESPN API error"},
        },
    )
    def post(self, request: Request) -> Response:
        """Ingest scoreboard data from ESPN."""
        serializer = IngestScoreboardRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sport = serializer.validated_data["sport"]
        league = serializer.validated_data["league"]
        date = serializer.validated_data.get("date")

        logger.info("scoreboard_ingestion_requested", sport=sport, league=league, date=date)

        service = ScoreboardIngestionService()
        result = service.ingest_scoreboard(sport, league, date)
        return Response(IngestionResultSerializer(result.to_dict()).data, status=status.HTTP_200_OK)


class IngestTeamsView(APIView):
    """Endpoint for ingesting team data from ESPN."""

    @extend_schema(
        tags=["Ingest"],
        summary="Ingest teams data",
        description=(
            "Fetch all teams from ESPN for a specific sport and league, "
            "then upsert them into the database."
        ),
        request=IngestTeamsRequestSerializer,
        responses={
            200: IngestionResultSerializer,
            400: {"description": "Invalid request data"},
            502: {"description": "ESPN API error"},
        },
    )
    def post(self, request: Request) -> Response:
        """Ingest teams data from ESPN."""
        serializer = IngestTeamsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sport = serializer.validated_data["sport"]
        league = serializer.validated_data["league"]

        logger.info("teams_ingestion_requested", sport=sport, league=league)

        service = TeamIngestionService()
        result = service.ingest_teams(sport, league)
        return Response(IngestionResultSerializer(result.to_dict()).data, status=status.HTTP_200_OK)


class IngestNewsView(APIView):
    """Endpoint for ingesting news articles from ESPN."""

    @extend_schema(
        tags=["Ingest"],
        summary="Ingest news articles",
        description=(
            "Fetch news articles from ESPN for a specific sport and league, "
            "then upsert them into the database."
        ),
        request=IngestNewsRequestSerializer,
        responses={
            200: IngestionResultSerializer,
            400: {"description": "Invalid request data"},
            502: {"description": "ESPN API error"},
        },
    )
    def post(self, request: Request) -> Response:
        """Ingest news articles from ESPN."""
        serializer = IngestNewsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sport = serializer.validated_data["sport"]
        league = serializer.validated_data["league"]
        limit = serializer.validated_data.get("limit", 50)

        logger.info("news_ingestion_requested", sport=sport, league=league, limit=limit)

        service = NewsIngestionService()
        result = service.ingest_news(sport, league, limit=limit)
        return Response(IngestionResultSerializer(result.to_dict()).data, status=status.HTTP_200_OK)


class IngestInjuriesView(APIView):
    """Endpoint for ingesting league injury reports from ESPN."""

    @extend_schema(
        tags=["Ingest"],
        summary="Ingest injury report",
        description=(
            "Fetch the current league injury report from ESPN and refresh the database snapshot. "
            "This is a full replacement — all prior entries for the league are deleted then re-inserted."
        ),
        request=IngestInjuriesRequestSerializer,
        responses={
            200: IngestionResultSerializer,
            400: {"description": "Invalid request data"},
            502: {"description": "ESPN API error"},
        },
    )
    def post(self, request: Request) -> Response:
        """Ingest injury report from ESPN."""
        serializer = IngestInjuriesRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sport = serializer.validated_data["sport"]
        league = serializer.validated_data["league"]

        logger.info("injuries_ingestion_requested", sport=sport, league=league)

        service = InjuryIngestionService()
        result = service.ingest_injuries(sport, league)
        return Response(IngestionResultSerializer(result.to_dict()).data, status=status.HTTP_200_OK)


class IngestTransactionsView(APIView):
    """Endpoint for ingesting league transactions from ESPN."""

    @extend_schema(
        tags=["Ingest"],
        summary="Ingest transactions",
        description=(
            "Fetch the latest transactions from ESPN for a specific sport and league, "
            "then upsert them into the database."
        ),
        request=IngestTransactionsRequestSerializer,
        responses={
            200: IngestionResultSerializer,
            400: {"description": "Invalid request data"},
            502: {"description": "ESPN API error"},
        },
    )
    def post(self, request: Request) -> Response:
        """Ingest transactions from ESPN."""
        serializer = IngestTransactionsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sport = serializer.validated_data["sport"]
        league = serializer.validated_data["league"]

        logger.info("transactions_ingestion_requested", sport=sport, league=league)

        service = TransactionIngestionService()
        result = service.ingest_transactions(sport, league)
        return Response(IngestionResultSerializer(result.to_dict()).data, status=status.HTTP_200_OK)

```

---

# FILE: `espn_service/clients/__init__.py`

```python
"""Clients package for external API integrations."""

from clients.espn_client import ESPNClient

__all__ = ["ESPNClient"]

```

---

# FILE: `espn_service/clients/espn_client.py`

```python
"""ESPN API client with retry logic, timeouts, and error handling.

This module provides a centralized client for all ESPN API interactions.
All ESPN API calls should go through this client to ensure consistent
error handling, retries, and rate limiting.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import httpx
import structlog
from django.conf import settings
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from apps.core.exceptions import (
    ESPNClientError,
    ESPNNotFoundError,
    ESPNRateLimitError,
)

logger = structlog.get_logger(__name__)


class ESPNEndpointDomain(str, Enum):
    """ESPN API domain types."""

    SITE = "site"          # site.api.espn.com
    CORE = "core"          # sports.core.api.espn.com
    SITE_V2 = "site_v2"    # site.api.espn.com/apis/v2/ — standings only
    WEB_V3 = "web_v3"      # site.web.api.espn.com/apis/common/v3/ — athlete data
    CDN = "cdn"            # cdn.espn.com/core/ — full game packages
    NOW = "now"            # now.core.api.espn.com/v1/ — real-time news


# ─────────────────────────────────────────────────────────────────────────────
# Sports & League Registry
# All 17 sports and 139 leagues discovered from the ESPN v2/v3 WADL.
# Format: "sport_slug": "Display Name"
# ─────────────────────────────────────────────────────────────────────────────

SPORT_NAMES: dict[str, str] = {
    "australian-football": "Australian Football",
    "baseball": "Baseball",
    "basketball": "Basketball",
    "cricket": "Cricket",
    "field-hockey": "Field Hockey",
    "football": "Football",
    "golf": "Golf",
    "hockey": "Hockey",
    "lacrosse": "Lacrosse",
    "mma": "Mixed Martial Arts",
    "racing": "Racing",
    "rugby": "Rugby",
    "rugby-league": "Rugby League",
    "soccer": "Soccer",
    "tennis": "Tennis",
    "volleyball": "Volleyball",
    "water-polo": "Water Polo",
}

# league_slug: (Display Name, Abbreviation)
LEAGUE_INFO: dict[str, tuple[str, str]] = {
    # Australian Football
    "afl": ("AFL", "AFL"),
    # Baseball
    "caribbean-series": ("Caribbean Series", "CAR"),
    "college-baseball": ("NCAA Baseball", "NCAAB"),
    "college-softball": ("NCAA Softball", "NCAAS"),
    "dominican-winter-league": ("Dominican Winter League", "DWL"),
    "llb": ("Little League Baseball", "LLB"),
    "lls": ("Little League Softball", "LLS"),
    "mexican-winter-league": ("Mexican League", "MLM"),
    "mlb": ("Major League Baseball", "MLB"),
    "olympics-baseball": ("Olympics Men's Baseball", "OLY"),
    "puerto-rican-winter-league": ("Puerto Rican Winter League", "PRWL"),
    "venezuelan-winter-league": ("Venezuelan Winter League", "VWL"),
    "world-baseball-classic": ("World Baseball Classic", "WBC"),
    # Basketball
    "fiba": ("FIBA World Cup", "FIBA"),
    "mens-college-basketball": ("NCAA Men's Basketball", "NCAAM"),
    "mens-olympics-basketball": ("Olympics Men's Basketball", "OLY"),
    "nba": ("National Basketball Association", "NBA"),
    "nba-development": ("NBA G League", "GLEA"),
    "nba-summer-california": ("NBA California Classic Summer League", "NBASL"),
    "nba-summer-golden-state": ("Golden State Summer League", "GSSL"),
    "nba-summer-las-vegas": ("Las Vegas Summer League", "LVSL"),
    "nba-summer-orlando": ("Orlando Summer League", "OSL"),
    "nba-summer-sacramento": ("Sacramento Summer League", "SASL"),
    "nba-summer-utah": ("Salt Lake City Summer League", "SLSL"),
    "nbl": ("National Basketball League", "NBL"),
    "wnba": ("Women's National Basketball Association", "WNBA"),
    "womens-college-basketball": ("NCAA Women's Basketball", "NCAAW"),
    "womens-olympics-basketball": ("Olympics Women's Basketball", "OLY"),
    # Field Hockey
    "womens-college-field-hockey": ("NCAA Women's Field Hockey", "NCAAFH"),
    # Football
    "cfl": ("Canadian Football League", "CFL"),
    "college-football": ("NCAA Football", "NCAAF"),
    "nfl": ("National Football League", "NFL"),
    "ufl": ("United Football League", "UFL"),
    "xfl": ("XFL", "XFL"),
    # Golf
    "champions-tour": ("PGA TOUR Champions", "CHAMP"),
    "eur": ("DP World Tour", "DP"),
    "liv": ("LIV Golf Invitational Series", "LIV"),
    "lpga": ("Ladies Pro Golf Association", "LPGA"),
    "mens-olympics-golf": ("Olympic Golf - Men", "OLY"),
    "ntw": ("Korn Ferry Tour", "KFT"),
    "pga": ("PGA TOUR", "PGA"),
    "tgl": ("TGL", "TGL"),
    "womens-olympics-golf": ("Olympic Golf - Women", "OLY"),
    # Hockey
    "hockey-world-cup": ("World Cup of Hockey", "WCOH"),
    "mens-college-hockey": ("NCAA Men's Ice Hockey", "NCAAH"),
    "nhl": ("National Hockey League", "NHL"),
    "olympics-mens-ice-hockey": ("Men's Ice Hockey Olympics", "OLY"),
    "olympics-womens-ice-hockey": ("Women's Ice Hockey Olympics", "OLY"),
    "womens-college-hockey": ("NCAA Women's Hockey", "NCAAWH"),
    # Lacrosse
    "mens-college-lacrosse": ("NCAA Men's Lacrosse", "NCAML"),
    "nll": ("National Lacrosse League", "NLL"),
    "pll": ("Premier Lacrosse League", "PLL"),
    "womens-college-lacrosse": ("NCAA Women's Lacrosse", "NCAWL"),
    # MMA
    "absolute": ("Absolute Championship Berkut", "ACB"),
    "affliction": ("Affliction", "AFF"),
    "bang-fighting": ("Bang Fighting Championships", "BFC"),
    "banni-fight": ("Banni Fight Combat", "BFC"),
    "banzay": ("Banzay Fight Championship", "BZY"),
    "barracao": ("Barracao Fight Championship", "BFC"),
    "battlezone": ("Battlezone Fighting Championships", "BZN"),
    "bellator": ("Bellator Fighting Championship", "BEL"),
    "benevides": ("Benevides Fight Championship", "BFG"),
    "big-fight": ("Big Fight Champions", "BFC"),
    "blackout": ("Blackout Fighting Championship", "BOF"),
    "bosnia": ("Bosnia Fight Championship", "BFC"),
    "boxe": ("Boxe Fight Combat", "BXE"),
    "brazilian-freestyle": ("Brazilian Freestyle Circuit", "BRC"),
    "budo": ("Budo Fighting Championships", "BDO"),
    "cage-warriors": ("Cage Warriors Fighting Championship", "CW"),
    "dream": ("Dream", "DRM"),
    "fng": ("Fight Nights Global", "FNG"),
    "ifc": ("Invicta FC", "IFC"),
    "ifl": ("International Fight League", "IFL"),
    "k1": ("K-1", "K1"),
    "ksw": ("Konfrontacja Sztuk Walki", "KSW"),
    "lfa": ("Legacy Fighting Alliance", "LFA"),
    "lfc": ("Legacy Fighting Championship", "LFC"),
    "m1": ("M-1 Mix-Fight Championship", "M1"),
    # Racing
    "f1": ("Formula 1", "F1"),
    "irl": ("IndyCar Series", "INDY"),
    "nascar-premier": ("NASCAR Cup Series", "CUP"),
    "nascar-secondary": ("NASCAR O'Reilly Auto Parts Series", "XFN"),
    "nascar-truck": ("NASCAR Truck Series", "TRUCK"),
    # Rugby (numeric IDs)
    "268565": ("British and Irish Lions Tour", "BILT"),
    "164205": ("Rugby World Cup", "RWC"),
    "180659": ("Six Nations", "6N"),
    "244293": ("The Rugby Championship", "TRC"),
    "271937": ("European Rugby Champions Cup", "EPCR"),
    "272073": ("European Rugby Challenge Cup", "ERCC"),
    "267979": ("Gallagher Premiership", "PREM"),
    "270557": ("United Rugby Championship", "URC"),
    "270559": ("French Top 14", "TOP14"),
    "2009": ("URBA Primera A", "URBA"),
    "242041": ("Super Rugby Pacific", "SRP"),
    "289271": ("Super Rugby Aotearoa", "SRA"),
    "289272": ("Super Rugby AU", "SRAU"),
    "289277": ("Super Rugby Trans-Tasman", "SRTT"),
    "289279": ("URBA Top 12", "T12"),
    "270555": ("Currie Cup", "CC"),
    "270563": ("Mitre 10 Cup", "M10"),
    "236461": ("Anglo-Welsh Cup", "AWC"),
    "289274": ("2020 Tri Nations", "TN"),
    "282": ("Olympic Men's 7s", "OLY"),
    "283": ("Olympic Women's Rugby Sevens", "OLY"),
    "289237": ("Women's Rugby World Cup", "WRWC"),
    "289262": ("Major League Rugby", "MLR"),
    "289234": ("International Test Match", "INT"),
    # Rugby League
    "3": ("Rugby League", "RL"),
    # Soccer
    "fifa.world": ("FIFA World Cup", "WC"),
    "fifa.wwc": ("FIFA Women's World Cup", "WWC"),
    "uefa.champions": ("UEFA Champions League", "UCL"),
    "eng.1": ("English Premier League", "EPL"),
    "eng.fa": ("English FA Cup", "FAC"),
    "eng.league_cup": ("English Carabao Cup", "ELC"),
    "esp.1": ("Spanish LALIGA", "LIGA"),
    "esp.super_cup": ("Spanish Supercopa", "SC"),
    "esp.copa_del_rey": ("Spanish Copa del Rey", "CDR"),
    "ger.1": ("German Bundesliga", "BUN"),
    "ger.dfb_pokal": ("German Cup", "DFB"),
    "usa.1": ("MLS", "MLS"),
    "concacaf.leagues.cup": ("Leagues Cup", "LC"),
    "campeones.cup": ("Campeones Cup", "CC"),
    "fifa.shebelieves": ("SheBelieves Cup", "SBC"),
    "fifa.w.champions_cup": ("FIFA Women's Champions Cup", "WCC"),
    "uefa.wchampions": ("UEFA Women's Champions League", "UWCL"),
    "usa.nwsl": ("NWSL", "NWSL"),
    "usa.nwsl.cup": ("NWSL Challenge Cup", "NWSLCC"),
    "uefa.europa": ("UEFA Europa League", "UEL"),
    "uefa.europa.conf": ("UEFA Conference League", "UECL"),
    "mex.1": ("Mexican Liga BBVA MX", "LIGAMX"),
    "ita.1": ("Italian Serie A", "SA"),
    "ita.coppa_italia": ("Coppa Italia", "CI"),
    "fra.1": ("French Ligue 1", "L1"),
    # Tennis
    "atp": ("ATP", "ATP"),
    "wta": ("WTA", "WTA"),
    # Volleyball
    "mens-college-volleyball": ("NCAA Men's Volleyball", "NCAMV"),
    "womens-college-volleyball": ("NCAA Women's Volleyball", "NCAWV"),
    # Water Polo
    "mens-college-water-polo": ("NCAA Men's Water Polo", "NCAMWP"),
    "womens-college-water-polo": ("NCAA Women's Water Polo", "NCAWWP"),
}


@dataclass
class ESPNResponse:
    """Wrapper for ESPN API responses."""

    data: dict[str, Any]
    status_code: int
    url: str

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300


class ESPNClient:
    """Client for ESPN API interactions.

    This client handles:
    - Multiple ESPN API domains (site, core v2, core v3)
    - Automatic retries with exponential backoff
    - Request timeouts
    - Rate limiting guidance
    - Defensive JSON parsing
    - Structured error responses

    Usage:
        client = ESPNClient()
        response = client.get_scoreboard("basketball", "nba", "20241215")
        teams = client.get_teams("basketball", "nba")
    """

    def __init__(
        self,
        site_api_url: str | None = None,
        core_api_url: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        user_agent: str | None = None,
    ):
        """Initialize ESPN client.

        Supports all discovered ESPN API domains:
        - site.api.espn.com          → scoreboard, teams, news, injuries, etc.
        - site.api.espn.com/apis/v2/ → standings (site/v2 returns a stub)
        - sports.core.api.espn.com   → core data, odds, play-by-play
        - site.web.api.espn.com      → athlete stats, gamelog, splits (common/v3)
        - cdn.espn.com/core/         → full game packages with drives/plays
        - now.core.api.espn.com/v1/  → real-time news feed

        Args:
            site_api_url: Base URL for site.api.espn.com
            core_api_url: Base URL for sports.core.api.espn.com
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            user_agent: User-Agent header value
        """
        config = getattr(settings, "ESPN_CLIENT", {})

        self.site_api_url = (
            site_api_url or config.get("SITE_API_BASE_URL", "https://site.api.espn.com")
        ).rstrip("/")
        self.core_api_url = (
            core_api_url or config.get("CORE_API_BASE_URL", "https://sports.core.api.espn.com")
        ).rstrip("/")
        self.web_v3_url = config.get(
            "WEB_V3_API_BASE_URL", "https://site.web.api.espn.com"
        ).rstrip("/")
        self.cdn_url = config.get(
            "CDN_API_BASE_URL", "https://cdn.espn.com"
        ).rstrip("/")
        self.now_url = config.get(
            "NOW_API_BASE_URL", "https://now.core.api.espn.com"
        ).rstrip("/")
        self.timeout = timeout or config.get("TIMEOUT", 30.0)
        self.max_retries = max_retries or config.get("MAX_RETRIES", 3)
        self.retry_backoff = config.get("RETRY_BACKOFF", 1.0)
        self.user_agent = user_agent or config.get(
            "USER_AGENT", "ESPN-Service/1.0"
        )

        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client (lazy initialization)."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "application/json",
                },
                follow_redirects=True,
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            self._client.close()
            self._client = None

    def __enter__(self) -> "ESPNClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def _get_base_url(self, domain: ESPNEndpointDomain) -> str:
        """Get base URL for the given domain."""
        if domain == ESPNEndpointDomain.SITE:
            return self.site_api_url
        if domain == ESPNEndpointDomain.SITE_V2:
            return self.site_api_url
        if domain == ESPNEndpointDomain.WEB_V3:
            return self.web_v3_url
        if domain == ESPNEndpointDomain.CDN:
            return self.cdn_url
        if domain == ESPNEndpointDomain.NOW:
            return self.now_url
        return self.core_api_url

    def _build_url(self, domain: ESPNEndpointDomain, path: str) -> str:
        """Build full URL from domain and path."""
        base_url = self._get_base_url(domain)
        path = path.lstrip("/")
        return f"{base_url}/{path}"

    def _handle_response(self, response: httpx.Response, url: str) -> ESPNResponse:
        """Handle HTTP response and convert to ESPNResponse.

        Args:
            response: HTTP response object
            url: Request URL (for logging)

        Returns:
            ESPNResponse with parsed data

        Raises:
            ESPNNotFoundError: If resource not found (404)
            ESPNRateLimitError: If rate limited (429)
            ESPNClientError: For other HTTP errors
        """
        if response.status_code == 404:
            logger.warning("espn_resource_not_found", url=url)
            raise ESPNNotFoundError(f"ESPN resource not found: {url}")

        if response.status_code == 429:
            logger.warning("espn_rate_limited", url=url)
            raise ESPNRateLimitError("ESPN API rate limit exceeded")

        if response.status_code >= 500:
            logger.error(
                "espn_server_error",
                url=url,
                status_code=response.status_code,
            )
            # Raise for retry
            raise ESPNClientError(f"ESPN server error: {response.status_code}")

        if response.status_code >= 400:
            logger.error(
                "espn_client_error",
                url=url,
                status_code=response.status_code,
            )
            raise ESPNClientError(f"ESPN API error: {response.status_code}")

        # Parse JSON response
        try:
            data = response.json()
        except Exception as e:
            logger.error("espn_json_parse_error", url=url, error=str(e))
            raise ESPNClientError(f"Failed to parse ESPN response: {e}") from e

        return ESPNResponse(data=data, status_code=response.status_code, url=url)

    def _request_with_retry(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
    ) -> ESPNResponse:
        """Make HTTP request with retry logic.

        This method implements exponential backoff retry for transient failures.
        """

        @retry(
            retry=retry_if_exception_type((httpx.TransportError, ESPNClientError)),
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=self.retry_backoff, min=1, max=10),
            reraise=True,
        )
        def _do_request() -> ESPNResponse:
            logger.debug("espn_request", method=method, url=url, params=params)
            response = self.client.request(method, url, params=params)
            return self._handle_response(response, url)

        try:
            return _do_request()
        except RetryError as e:
            logger.error(
                "espn_request_failed_after_retries",
                url=url,
                retries=self.max_retries,
            )
            raise ESPNClientError(
                f"ESPN request failed after {self.max_retries} retries"
            ) from e
        except (ESPNNotFoundError, ESPNRateLimitError):
            # These should not be retried, re-raise directly
            raise
        except httpx.TransportError as e:
            logger.error("espn_transport_error", url=url, error=str(e))
            raise ESPNClientError(f"ESPN connection error: {e}") from e

    def get(
        self,
        path: str,
        domain: ESPNEndpointDomain = ESPNEndpointDomain.SITE,
        params: dict[str, Any] | None = None,
    ) -> ESPNResponse:
        """Make GET request to ESPN API.

        Args:
            path: API path (e.g., "/apis/site/v2/sports/basketball/nba/scoreboard")
            domain: Which ESPN domain to use
            params: Query parameters

        Returns:
            ESPNResponse with parsed data
        """
        url = self._build_url(domain, path)
        return self._request_with_retry("GET", url, params=params)

    # --------------------- Scoreboard Endpoints ---------------------

    def get_scoreboard(
        self,
        sport: str,
        league: str,
        date: str | datetime | None = None,
        limit: int | None = None,
    ) -> ESPNResponse:
        """Get scoreboard/schedule for a sport and league.

        Args:
            sport: Sport slug (e.g., "basketball", "football")
            league: League slug (e.g., "nba", "nfl")
            date: Date to get scoreboard for (YYYYMMDD format or datetime)
            limit: Maximum number of events to return

        Returns:
            ESPNResponse with scoreboard data
        """
        path = f"/apis/site/v2/sports/{sport}/{league}/scoreboard"
        params: dict[str, Any] = {}

        if date:
            if isinstance(date, datetime):
                date = date.strftime("%Y%m%d")
            params["dates"] = date

        if limit:
            params["limit"] = limit

        logger.info(
            "fetching_scoreboard",
            sport=sport,
            league=league,
            date=date,
        )
        return self.get(path, domain=ESPNEndpointDomain.SITE, params=params)

    # --------------------- Team Endpoints ---------------------

    def get_teams(
        self,
        sport: str,
        league: str,
        limit: int = 100,
    ) -> ESPNResponse:
        """Get all teams for a sport and league.

        Args:
            sport: Sport slug (e.g., "basketball", "football")
            league: League slug (e.g., "nba", "nfl")
            limit: Maximum number of teams to return

        Returns:
            ESPNResponse with teams data
        """
        path = f"/apis/site/v2/sports/{sport}/{league}/teams"
        params = {"limit": limit}

        logger.info("fetching_teams", sport=sport, league=league)
        return self.get(path, domain=ESPNEndpointDomain.SITE, params=params)

    def get_team(
        self,
        sport: str,
        league: str,
        team_id: str,
    ) -> ESPNResponse:
        """Get details for a specific team.

        Args:
            sport: Sport slug
            league: League slug
            team_id: ESPN team ID

        Returns:
            ESPNResponse with team details
        """
        path = f"/apis/site/v2/sports/{sport}/{league}/teams/{team_id}"

        logger.info(
            "fetching_team",
            sport=sport,
            league=league,
            team_id=team_id,
        )
        return self.get(path, domain=ESPNEndpointDomain.SITE)

    def get_team_roster(
        self,
        sport: str,
        league: str,
        team_id: str,
    ) -> ESPNResponse:
        """Get roster for a specific team.

        Args:
            sport: Sport slug
            league: League slug
            team_id: ESPN team ID

        Returns:
            ESPNResponse with roster data
        """
        path = f"/apis/site/v2/sports/{sport}/{league}/teams/{team_id}/roster"
        logger.info("fetching_team_roster", sport=sport, league=league, team_id=team_id)
        return self.get(path, domain=ESPNEndpointDomain.SITE)

    # --------------------- Event/Game Endpoints ---------------------

    def get_event(
        self,
        sport: str,
        league: str,
        event_id: str,
    ) -> ESPNResponse:
        """Get details for a specific event/game.

        Args:
            sport: Sport slug
            league: League slug
            event_id: ESPN event ID

        Returns:
            ESPNResponse with event details
        """
        path = f"/apis/site/v2/sports/{sport}/{league}/summary"
        params = {"event": event_id}

        logger.info(
            "fetching_event",
            sport=sport,
            league=league,
            event_id=event_id,
        )
        return self.get(path, domain=ESPNEndpointDomain.SITE, params=params)

    def get_news(
        self,
        sport: str,
        league: str,
        limit: int = 25,
    ) -> ESPNResponse:
        """Get news for a sport and league.

        Args:
            sport: Sport slug
            league: League slug
            limit: Number of articles to return

        Returns:
            ESPNResponse with news data
        """
        path = f"/apis/site/v2/sports/{sport}/{league}/news"
        params: dict[str, Any] = {"limit": limit}
        logger.info("fetching_news", sport=sport, league=league)
        return self.get(path, domain=ESPNEndpointDomain.SITE, params=params)

    def get_standings(
        self,
        sport: str,
        league: str,
        season: int | None = None,
    ) -> ESPNResponse:
        """Get league standings.

        Uses /apis/v2/ domain — /apis/site/v2/ standings only returns a stub.
        Rugby Union standings are not available via this domain; use get_core_standings().

        Args:
            sport: Sport slug
            league: League slug
            season: Season year (optional)

        Returns:
            ESPNResponse with standings data
        """
        # NOTE: /apis/site/v2/ returns only a stub {"fullViewLink": {...}}
        # Use /apis/v2/ which returns the full standings tree
        path = f"/apis/v2/sports/{sport}/{league}/standings"
        params: dict[str, Any] = {}
        if season:
            params["season"] = season
        logger.info("fetching_standings", sport=sport, league=league)
        return self.get(path, domain=ESPNEndpointDomain.SITE, params=params)

    def get_rankings(
        self,
        sport: str,
        league: str,
    ) -> ESPNResponse:
        """Get league rankings (college sports).

        Args:
            sport: Sport slug
            league: League slug

        Returns:
            ESPNResponse with rankings data
        """
        path = f"/apis/site/v2/sports/{sport}/{league}/rankings"
        logger.info("fetching_rankings", sport=sport, league=league)
        return self.get(path, domain=ESPNEndpointDomain.SITE)

    # --------------------- Core API v2 Endpoints ---------------------

    def get_league_info(
        self,
        sport: str,
        league: str,
    ) -> ESPNResponse:
        """Get league information from core API.

        Args:
            sport: Sport slug
            league: League slug

        Returns:
            ESPNResponse with league information
        """
        path = f"/v2/sports/{sport}/leagues/{league}"

        logger.info("fetching_league_info", sport=sport, league=league)
        return self.get(path, domain=ESPNEndpointDomain.CORE)

    def get_athletes(
        self,
        sport: str,
        league: str,
        team_id: str | None = None,
        limit: int = 100,
        page: int = 1,
        active: bool | None = None,
    ) -> ESPNResponse:
        """Get athletes from core API.

        Args:
            sport: Sport slug
            league: League slug
            team_id: Optional team ID to filter by
            limit: Maximum number of athletes
            page: Page number for pagination
            active: Filter by active status

        Returns:
            ESPNResponse with athletes data
        """
        path = f"/v2/sports/{sport}/leagues/{league}/athletes"
        params: dict[str, Any] = {"limit": limit, "page": page}

        if team_id:
            params["teams"] = team_id
        if active is not None:
            params["active"] = "true" if active else "false"

        logger.info(
            "fetching_athletes",
            sport=sport,
            league=league,
            team_id=team_id,
        )
        return self.get(path, domain=ESPNEndpointDomain.CORE, params=params)

    def get_athlete(
        self,
        sport: str,
        league: str,
        athlete_id: str | int,
    ) -> ESPNResponse:
        """Get a single athlete from the core API.

        Args:
            sport: Sport slug
            league: League slug
            athlete_id: ESPN athlete ID

        Returns:
            ESPNResponse with athlete data
        """
        path = f"/v2/sports/{sport}/leagues/{league}/athletes/{athlete_id}"
        logger.info("fetching_athlete", sport=sport, league=league, athlete_id=athlete_id)
        return self.get(path, domain=ESPNEndpointDomain.CORE)

    def get_athlete_statistics(
        self,
        sport: str,
        league: str,
        athlete_id: str | int,
        season_type: str | None = None,
    ) -> ESPNResponse:
        """Get career statistics for an athlete.

        Args:
            sport: Sport slug
            league: League slug
            athlete_id: ESPN athlete ID
            season_type: Season type (e.g., "2" for regular season)

        Returns:
            ESPNResponse with statistics data
        """
        path = f"/v2/sports/{sport}/leagues/{league}/athletes/{athlete_id}/statistics"
        params: dict[str, Any] = {}
        if season_type:
            params["seasonType"] = season_type
        return self.get(path, domain=ESPNEndpointDomain.CORE, params=params)

    def get_core_events(
        self,
        sport: str,
        league: str,
        dates: str | None = None,
        limit: int = 100,
        page: int = 1,
    ) -> ESPNResponse:
        """Get events from the core API (more detailed than site API).

        Args:
            sport: Sport slug
            league: League slug
            dates: Date or range filter (e.g., "2024" or "20241215")
            limit: Maximum results per page
            page: Page number

        Returns:
            ESPNResponse with events data
        """
        path = f"/v2/sports/{sport}/leagues/{league}/events"
        params: dict[str, Any] = {"limit": limit, "page": page}
        if dates:
            params["dates"] = dates
        return self.get(path, domain=ESPNEndpointDomain.CORE, params=params)

    def get_seasons(
        self,
        sport: str,
        league: str,
        limit: int = 20,
    ) -> ESPNResponse:
        """Get seasons list for a league.

        Args:
            sport: Sport slug
            league: League slug
            limit: Maximum number of seasons

        Returns:
            ESPNResponse with seasons data
        """
        path = f"/v2/sports/{sport}/leagues/{league}/seasons"
        params: dict[str, Any] = {"limit": limit}
        return self.get(path, domain=ESPNEndpointDomain.CORE, params=params)

    def get_core_teams(
        self,
        sport: str,
        league: str,
        limit: int = 100,
        page: int = 1,
    ) -> ESPNResponse:
        """Get teams from the core API.

        Args:
            sport: Sport slug
            league: League slug
            limit: Results per page
            page: Page number

        Returns:
            ESPNResponse with teams data
        """
        path = f"/v2/sports/{sport}/leagues/{league}/teams"
        params: dict[str, Any] = {"limit": limit, "page": page}
        return self.get(path, domain=ESPNEndpointDomain.CORE, params=params)

    def get_core_standings(
        self,
        sport: str,
        league: str,
        season: int | None = None,
        season_type: int | None = None,
    ) -> ESPNResponse:
        """Get standings from the core API.

        Args:
            sport: Sport slug
            league: League slug
            season: Season year
            season_type: 1=pre, 2=regular, 3=post

        Returns:
            ESPNResponse with standings data
        """
        params: dict[str, Any] = {}
        if season and season_type:
            path = (
                f"/v2/sports/{sport}/leagues/{league}"
                f"/seasons/{season}/types/{season_type}/groups/standings"
            )
        elif season:
            path = f"/v2/sports/{sport}/leagues/{league}/seasons/{season}/standings"
        else:
            path = f"/v2/sports/{sport}/leagues/{league}/standings"
        return self.get(path, domain=ESPNEndpointDomain.CORE, params=params)

    def get_odds(
        self,
        sport: str,
        league: str,
        event_id: str,
        competition_id: str | None = None,
    ) -> ESPNResponse:
        """Get betting odds for a game.

        Args:
            sport: Sport slug
            league: League slug
            event_id: ESPN event ID
            competition_id: Competition ID (usually same as event_id)

        Returns:
            ESPNResponse with odds data
        """
        comp_id = competition_id or event_id
        path = (
            f"/v2/sports/{sport}/leagues/{league}"
            f"/events/{event_id}/competitions/{comp_id}/odds"
        )
        logger.info("fetching_odds", sport=sport, league=league, event_id=event_id)
        return self.get(path, domain=ESPNEndpointDomain.CORE)

    def get_win_probabilities(
        self,
        sport: str,
        league: str,
        event_id: str,
        competition_id: str | None = None,
    ) -> ESPNResponse:
        """Get win probabilities for a game.

        Args:
            sport: Sport slug
            league: League slug
            event_id: ESPN event ID
            competition_id: Competition ID (usually same as event_id)

        Returns:
            ESPNResponse with probability data
        """
        comp_id = competition_id or event_id
        path = (
            f"/v2/sports/{sport}/leagues/{league}"
            f"/events/{event_id}/competitions/{comp_id}/probabilities"
        )
        return self.get(path, domain=ESPNEndpointDomain.CORE)

    def get_plays(
        self,
        sport: str,
        league: str,
        event_id: str,
        competition_id: str | None = None,
        limit: int = 400,
    ) -> ESPNResponse:
        """Get play-by-play data for a game.

        Args:
            sport: Sport slug
            league: League slug
            event_id: ESPN event ID
            competition_id: Competition ID (usually same as event_id)
            limit: Max plays to return

        Returns:
            ESPNResponse with play data
        """
        comp_id = competition_id or event_id
        path = (
            f"/v2/sports/{sport}/leagues/{league}"
            f"/events/{event_id}/competitions/{comp_id}/plays"
        )
        params: dict[str, Any] = {"limit": limit}
        return self.get(path, domain=ESPNEndpointDomain.CORE, params=params)

    def get_venues(
        self,
        sport: str,
        league: str,
        limit: int = 500,
    ) -> ESPNResponse:
        """Get venues for a league.

        Args:
            sport: Sport slug
            league: League slug
            limit: Maximum venues to return

        Returns:
            ESPNResponse with venue data
        """
        path = f"/v2/sports/{sport}/leagues/{league}/venues"
        params: dict[str, Any] = {"limit": limit}
        return self.get(path, domain=ESPNEndpointDomain.CORE, params=params)

    def get_leaders(
        self,
        sport: str,
        league: str,
        season: int | None = None,
        season_type: int | None = None,
    ) -> ESPNResponse:
        """Get statistical leaders for a league.

        Args:
            sport: Sport slug
            league: League slug
            season: Season year
            season_type: 1=pre, 2=regular, 3=post

        Returns:
            ESPNResponse with leaders data
        """
        params: dict[str, Any] = {}
        if season and season_type:
            path = (
                f"/v2/sports/{sport}/leagues/{league}"
                f"/seasons/{season}/types/{season_type}/leaders"
            )
        else:
            path = f"/v2/sports/{sport}/leagues/{league}/leaders"
        return self.get(path, domain=ESPNEndpointDomain.CORE, params=params)

    # --------------------- Core API v3 Endpoints ---------------------

    def get_athletes_v3(
        self,
        sport: str,
        league: str,
        limit: int = 1000,
        active: bool | None = True,
        page: int = 1,
    ) -> ESPNResponse:
        """Get athletes from the v3 core API (richer data).

        Args:
            sport: Sport slug
            league: League slug
            limit: Max athletes
            active: Filter by active status
            page: Page number

        Returns:
            ESPNResponse with athletes data
        """
        path = f"/v3/sports/{sport}/{league}/athletes"
        params: dict[str, Any] = {"limit": limit, "page": page}
        if active is not None:
            params["active"] = "true" if active else "false"
        logger.info("fetching_athletes_v3", sport=sport, league=league)
        return self.get(path, domain=ESPNEndpointDomain.CORE, params=params)

    def get_leaders_v3(
        self,
        sport: str,
        league: str,
    ) -> ESPNResponse:
        """Get statistical leaders from v3 API.

        Args:
            sport: Sport slug
            league: League slug

        Returns:
            ESPNResponse with leaders data
        """
        path = f"/v3/sports/{sport}/{league}/leaders"
        return self.get(path, domain=ESPNEndpointDomain.CORE)

    # --------------------- Team Sub-Resource Endpoints ---------------------

    def get_team_injuries(
        self,
        sport: str,
        league: str,
        team_id: str,
    ) -> ESPNResponse:
        """Get injury report for a specific team.

        Args:
            sport: Sport slug (e.g., "football", "basketball")
            league: League slug (e.g., "nfl", "nba")
            team_id: ESPN team ID

        Returns:
            ESPNResponse with injury data
        """
        path = f"/apis/site/v2/sports/{sport}/{league}/teams/{team_id}/injuries"
        logger.info("fetching_team_injuries", sport=sport, league=league, team_id=team_id)
        return self.get(path, domain=ESPNEndpointDomain.SITE)

    def get_team_depth_chart(
        self,
        sport: str,
        league: str,
        team_id: str,
    ) -> ESPNResponse:
        """Get depth chart for a specific team.

        Args:
            sport: Sport slug (e.g., "football", "basketball")
            league: League slug (e.g., "nfl", "nba")
            team_id: ESPN team ID

        Returns:
            ESPNResponse with depth chart data grouped by position
        """
        path = f"/apis/site/v2/sports/{sport}/{league}/teams/{team_id}/depthcharts"
        logger.info("fetching_team_depth_chart", sport=sport, league=league, team_id=team_id)
        return self.get(path, domain=ESPNEndpointDomain.SITE)

    def get_team_transactions(
        self,
        sport: str,
        league: str,
        team_id: str,
    ) -> ESPNResponse:
        """Get recent transactions/moves for a specific team.

        Args:
            sport: Sport slug
            league: League slug
            team_id: ESPN team ID

        Returns:
            ESPNResponse with transaction data
        """
        path = f"/apis/site/v2/sports/{sport}/{league}/teams/{team_id}/transactions"
        logger.info("fetching_team_transactions", sport=sport, league=league, team_id=team_id)
        return self.get(path, domain=ESPNEndpointDomain.SITE)

    # --------------------- Game Situation Endpoints ---------------------

    def get_game_situation(
        self,
        sport: str,
        league: str,
        event_id: str,
        competition_id: str | None = None,
    ) -> ESPNResponse:
        """Get current game situation (down, distance, possession, etc.).

        Args:
            sport: Sport slug
            league: League slug
            event_id: ESPN event ID
            competition_id: Competition ID (defaults to event_id)

        Returns:
            ESPNResponse with current game situation data
        """
        comp_id = competition_id or event_id
        path = (
            f"/v2/sports/{sport}/leagues/{league}"
            f"/events/{event_id}/competitions/{comp_id}/situation"
        )
        return self.get(path, domain=ESPNEndpointDomain.CORE)

    def get_game_predictor(
        self,
        sport: str,
        league: str,
        event_id: str,
        competition_id: str | None = None,
    ) -> ESPNResponse:
        """Get ESPN game predictor (projected winner/score) for a game.

        Args:
            sport: Sport slug
            league: League slug
            event_id: ESPN event ID
            competition_id: Competition ID (defaults to event_id)

        Returns:
            ESPNResponse with predictor data
        """
        comp_id = competition_id or event_id
        path = (
            f"/v2/sports/{sport}/leagues/{league}"
            f"/events/{event_id}/competitions/{comp_id}/predictor"
        )
        return self.get(path, domain=ESPNEndpointDomain.CORE)

    def get_game_broadcasts(
        self,
        sport: str,
        league: str,
        event_id: str,
        competition_id: str | None = None,
    ) -> ESPNResponse:
        """Get broadcast network info for a game.

        Args:
            sport: Sport slug
            league: League slug
            event_id: ESPN event ID
            competition_id: Competition ID (defaults to event_id)

        Returns:
            ESPNResponse with broadcast network data
        """
        comp_id = competition_id or event_id
        path = (
            f"/v2/sports/{sport}/leagues/{league}"
            f"/events/{event_id}/competitions/{comp_id}/broadcasts"
        )
        return self.get(path, domain=ESPNEndpointDomain.CORE)

    # --------------------- Coaches Endpoints ---------------------

    def get_coaches(
        self,
        sport: str,
        league: str,
        season: int | None = None,
        limit: int = 100,
    ) -> ESPNResponse:
        """Get coaching staff for a league season.

        Args:
            sport: Sport slug
            league: League slug
            season: Season year (uses current season if None)
            limit: Maximum coaches to return

        Returns:
            ESPNResponse with coaches data
        """
        if season:
            path = f"/v2/sports/{sport}/leagues/{league}/seasons/{season}/coaches"
        else:
            path = f"/v2/sports/{sport}/leagues/{league}/coaches"
        params: dict[str, Any] = {"limit": limit}
        logger.info("fetching_coaches", sport=sport, league=league, season=season)
        return self.get(path, domain=ESPNEndpointDomain.CORE, params=params)

    def get_coach(
        self,
        sport: str,
        league: str,
        coach_id: str,
    ) -> ESPNResponse:
        """Get a single coach's profile.

        Args:
            sport: Sport slug
            league: League slug
            coach_id: ESPN coach ID

        Returns:
            ESPNResponse with coach data
        """
        path = f"/v2/sports/{sport}/leagues/{league}/coaches/{coach_id}"
        return self.get(path, domain=ESPNEndpointDomain.CORE)

    # --------------------- QBR Endpoint ---------------------

    def get_qbr(
        self,
        league: str,
        season: int,
        season_type: int = 2,
        group: int = 1,
        split: int = 0,
        week: int | None = None,
    ) -> ESPNResponse:
        """Get ESPN Total Quarterback Rating (QBR) data.

        Only applicable to football leagues (nfl, college-football).

        Args:
            league: League slug ("nfl" or "college-football")
            season: Season year (e.g., 2024)
            season_type: 1=pre, 2=regular, 3=post
            group: Conference group ID (1=NFL, 80=FBS for NCAAF)
            split: 0=totals, 1=home, 2=away
            week: Optional week number (returns weekly QBR if provided)

        Returns:
            ESPNResponse with QBR data
        """
        if week is not None:
            path = (
                f"/v2/sports/football/leagues/{league}"
                f"/seasons/{season}/types/{season_type}/weeks/{week}/qbr/{split}"
            )
        else:
            path = (
                f"/v2/sports/football/leagues/{league}"
                f"/seasons/{season}/types/{season_type}/groups/{group}/qbr/{split}"
            )
        logger.info("fetching_qbr", league=league, season=season, week=week)
        return self.get(path, domain=ESPNEndpointDomain.CORE)

    # --------------------- Power Index Endpoint ---------------------

    def get_power_index(
        self,
        sport: str,
        league: str,
        season: int,
        team_id: str | None = None,
    ) -> ESPNResponse:
        """Get ESPN Power Index (BPI/SP+/FPI) data.

        Args:
            sport: Sport slug
            league: League slug
            season: Season year
            team_id: Optional team ID (returns league-wide data if None)

        Returns:
            ESPNResponse with power index data
        """
        if team_id:
            path = (
                f"/v2/sports/{sport}/leagues/{league}"
                f"/seasons/{season}/powerindex/{team_id}"
            )
        else:
            path = f"/v2/sports/{sport}/leagues/{league}/seasons/{season}/powerindex"
        logger.info("fetching_power_index", sport=sport, league=league, season=season)
        return self.get(path, domain=ESPNEndpointDomain.CORE)



    # --------------------- League-wide Site API Endpoints ---------------------

    def get_league_injuries(
        self,
        sport: str,
        league: str,
    ) -> ESPNResponse:
        """Get league-wide injury report (all teams).

        Not supported for MMA, Tennis, Golf (returns 500).

        Args:
            sport: Sport slug (e.g., "basketball", "football")
            league: League slug (e.g., "nba", "nfl")

        Returns:
            ESPNResponse with injuries grouped by team
        """
        path = f"/apis/site/v2/sports/{sport}/{league}/injuries"
        logger.info("fetching_league_injuries", sport=sport, league=league)
        return self.get(path, domain=ESPNEndpointDomain.SITE)

    def get_league_transactions(
        self,
        sport: str,
        league: str,
    ) -> ESPNResponse:
        """Get recent league-wide transactions (signings, trades, waivers).

        Args:
            sport: Sport slug
            league: League slug

        Returns:
            ESPNResponse with transaction data
        """
        path = f"/apis/site/v2/sports/{sport}/{league}/transactions"
        logger.info("fetching_league_transactions", sport=sport, league=league)
        return self.get(path, domain=ESPNEndpointDomain.SITE)

    def get_groups(
        self,
        sport: str,
        league: str,
    ) -> ESPNResponse:
        """Get conference/division groups for a league.

        Args:
            sport: Sport slug
            league: League slug

        Returns:
            ESPNResponse with group/conference data
        """
        path = f"/apis/site/v2/sports/{sport}/{league}/groups"
        logger.info("fetching_groups", sport=sport, league=league)
        return self.get(path, domain=ESPNEndpointDomain.SITE)

    # --------------------- common/v3 Athlete Endpoints ---------------------

    def get_athlete_overview(
        self,
        sport: str,
        league: str,
        athlete_id: str | int,
    ) -> ESPNResponse:
        """Get athlete overview (stats snapshot, next game, rotowire notes, news).

        Uses site.web.api.espn.com/apis/common/v3/. Confirmed working for:
        NFL, NBA, NHL, MLB. Soccer returns minimal data.

        Args:
            sport: Sport slug
            league: League slug
            athlete_id: ESPN athlete ID

        Returns:
            ESPNResponse with overview data
        """
        path = f"/apis/common/v3/sports/{sport}/{league}/athletes/{athlete_id}/overview"
        logger.info("fetching_athlete_overview", sport=sport, league=league, athlete_id=athlete_id)
        return self.get(path, domain=ESPNEndpointDomain.WEB_V3)

    def get_athlete_stats(
        self,
        sport: str,
        league: str,
        athlete_id: str | int,
        season: int | None = None,
        season_type: int | None = None,
    ) -> ESPNResponse:
        """Get season stats for an athlete.

        Uses site.web.api.espn.com/apis/common/v3/. Confirmed working for:
        NFL, NBA, NHL, MLB. Returns 404 for Soccer.

        Args:
            sport: Sport slug
            league: League slug
            athlete_id: ESPN athlete ID
            season: Season year (optional)
            season_type: 1=pre, 2=regular, 3=post (optional)

        Returns:
            ESPNResponse with stats (filters, teams, categories, glossary)
        """
        path = f"/apis/common/v3/sports/{sport}/{league}/athletes/{athlete_id}/stats"
        params: dict[str, Any] = {}
        if season:
            params["season"] = season
        if season_type:
            params["seasontype"] = season_type
        logger.info("fetching_athlete_stats", sport=sport, league=league, athlete_id=athlete_id)
        return self.get(path, domain=ESPNEndpointDomain.WEB_V3, params=params)

    def get_athlete_gamelog(
        self,
        sport: str,
        league: str,
        athlete_id: str | int,
        season: int | None = None,
    ) -> ESPNResponse:
        """Get game-by-game log for an athlete.

        Uses site.web.api.espn.com/apis/common/v3/. Confirmed working for:
        NFL, NBA, MLB. Returns 404 for NHL, 400 for Soccer.

        Args:
            sport: Sport slug
            league: League slug
            athlete_id: ESPN athlete ID
            season: Season year (optional)

        Returns:
            ESPNResponse with events/gamelog data
        """
        path = f"/apis/common/v3/sports/{sport}/{league}/athletes/{athlete_id}/gamelog"
        params: dict[str, Any] = {}
        if season:
            params["season"] = season
        logger.info("fetching_athlete_gamelog", sport=sport, league=league, athlete_id=athlete_id)
        return self.get(path, domain=ESPNEndpointDomain.WEB_V3, params=params)

    def get_athlete_splits(
        self,
        sport: str,
        league: str,
        athlete_id: str | int,
        season: int | None = None,
        season_type: int | None = None,
    ) -> ESPNResponse:
        """Get home/away/opponent splits for an athlete.

        Uses site.web.api.espn.com/apis/common/v3/. Confirmed working for:
        NFL, NBA, NHL, MLB. Not available for Soccer.

        Args:
            sport: Sport slug
            league: League slug
            athlete_id: ESPN athlete ID
            season: Season year (optional)
            season_type: 1=pre, 2=regular, 3=post (optional)

        Returns:
            ESPNResponse with splits by category (home/away/opponent)
        """
        path = f"/apis/common/v3/sports/{sport}/{league}/athletes/{athlete_id}/splits"
        params: dict[str, Any] = {}
        if season:
            params["season"] = season
        if season_type:
            params["seasontype"] = season_type
        logger.info("fetching_athlete_splits", sport=sport, league=league, athlete_id=athlete_id)
        return self.get(path, domain=ESPNEndpointDomain.WEB_V3, params=params)

    def get_statistics_by_athlete(
        self,
        sport: str,
        league: str,
        season: int | None = None,
        season_type: int | None = None,
        category: str | None = None,
        sort: str | None = None,
        limit: int = 50,
        page: int = 1,
    ) -> ESPNResponse:
        """Get ranked statistics leaderboard across all athletes.

        Uses site.web.api.espn.com/apis/common/v3/. Confirmed working for:
        NBA, NFL, NHL, MLB.

        Args:
            sport: Sport slug
            league: League slug
            season: Season year (optional)
            season_type: 1=pre, 2=regular, 3=post (optional)
            category: Stat category (e.g., "batting" for MLB, "passing" for NFL)
            sort: Sort field (e.g., "batting.homeRuns:desc")
            limit: Athletes per page
            page: Page number

        Returns:
            ESPNResponse with ranked athlete statistics
        """
        path = f"/apis/common/v3/sports/{sport}/{league}/statistics/byathlete"
        params: dict[str, Any] = {"limit": limit, "page": page}
        if season:
            params["season"] = season
        if season_type:
            params["seasontype"] = season_type
        if category:
            params["category"] = category
        if sort:
            params["sort"] = sort
        logger.info("fetching_statistics_by_athlete", sport=sport, league=league)
        return self.get(path, domain=ESPNEndpointDomain.WEB_V3, params=params)

    # --------------------- CDN Game Data Endpoints ---------------------

    def get_cdn_game(
        self,
        sport: str,
        game_id: str,
        view: str = "game",
    ) -> ESPNResponse:
        """Get full game package from cdn.espn.com.

        Returns a rich gamepackageJSON object containing drives, plays,
        scoring summary, win probability, boxscore, betting odds, and more.
        Requires ?xhr=1 (automatically added).

        Confirmed working for: nfl, nba, mlb, college-football.
        Soccer: use get_cdn_soccer_scoreboard() with a league param.

        Args:
            sport: ESPN CDN sport slug (e.g., "nfl", "nba", "mlb",
                   "college-football")
            game_id: ESPN event/game ID
            view: One of "game" (full), "boxscore", "playbyplay", "matchup"

        Returns:
            ESPNResponse containing gamepackageJSON key with all game data
        """
        path = f"/core/{sport}/{view}"
        params: dict[str, Any] = {"xhr": 1, "gameId": game_id}
        logger.info("fetching_cdn_game", sport=sport, game_id=game_id, view=view)
        return self.get(path, domain=ESPNEndpointDomain.CDN, params=params)

    def get_cdn_scoreboard(
        self,
        sport: str,
        league: str | None = None,
    ) -> ESPNResponse:
        """Get scoreboard via CDN domain.

        Args:
            sport: ESPN CDN sport slug (e.g., "nfl", "nba", "mlb",
                   "college-football", "soccer")
            league: League slug — only needed for soccer (e.g., "eng.1")

        Returns:
            ESPNResponse with scoreboard data
        """
        path = f"/core/{sport}/scoreboard"
        params: dict[str, Any] = {"xhr": 1}
        if league:
            params["league"] = league
        logger.info("fetching_cdn_scoreboard", sport=sport)
        return self.get(path, domain=ESPNEndpointDomain.CDN, params=params)

    # --------------------- Now/News Endpoints ---------------------

    def get_now_news(
        self,
        sport: str | None = None,
        league: str | None = None,
        team: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ESPNResponse:
        """Get real-time news from now.core.api.espn.com.

        Supports filtering by sport, league, or team. Returns a feed of
        articles with categories, images, and publication timestamps.

        Args:
            sport: Sport filter (e.g., "football", "basketball")
            league: League filter (e.g., "nfl", "nba")
            team: Team abbreviation filter (e.g., "dal", "gsw")
            limit: Number of articles (max 50)
            offset: Pagination offset

        Returns:
            ESPNResponse with resultsCount, resultsLimit, feed[]
        """
        path = "/v1/sports/news"
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if sport:
            params["sport"] = sport
        if league:
            params["league"] = league
        if team:
            params["team"] = team
        logger.info("fetching_now_news", sport=sport, league=league, team=team)
        return self.get(path, domain=ESPNEndpointDomain.NOW, params=params)


# Default singleton instance
_default_client: ESPNClient | None = None


def get_espn_client() -> ESPNClient:
    """Get the default ESPN client instance.

    Returns:
        ESPNClient singleton instance
    """
    global _default_client
    if _default_client is None:
        _default_client = ESPNClient()
    return _default_client

```

---

# FILE: `espn_service/config/__init__.py`

```python
# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from config.celery import app as celery_app

__all__ = ("celery_app",)

```

---

# FILE: `espn_service/config/asgi.py`

```python
"""ASGI config for espn_service project."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

application = get_asgi_application()

```

---

# FILE: `espn_service/config/celery.py`

```python
"""Celery configuration for espn_service."""

import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("espn_service")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self) -> None:
    """Debug task for testing Celery connectivity."""
    print(f"Request: {self.request!r}")

```

---

# FILE: `espn_service/config/settings/__init__.py`

```python
# Settings package

```

---

# FILE: `espn_service/config/settings/base.py`

```python
"""Base settings for espn_service project.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/
"""

import os
from pathlib import Path
from typing import Any

import environ
import structlog

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Initialize django-environ
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    CORS_ALLOWED_ORIGINS=(list, []),
)

# Read .env file if it exists
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY", default="django-insecure-change-me-in-production")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG")

ALLOWED_HOSTS: list[str] = env.list("ALLOWED_HOSTS", default=[])


# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
]

LOCAL_APPS = [
    "apps.core",
    "apps.espn",
    "apps.ingest",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.RequestIDMiddleware",
    "apps.core.middleware.StructuredLoggingMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
DATABASES = {
    "default": env.db("DATABASE_URL", default="sqlite:///db.sqlite3"),
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Django REST Framework
REST_FRAMEWORK: dict[str, Any] = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
}


# DRF Spectacular (OpenAPI/Swagger)
SPECTACULAR_SETTINGS = {
    "TITLE": "ESPN Service API",
    "DESCRIPTION": "Production-ready REST API for ESPN sports data ingestion and querying",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api/v1/",
    "TAGS": [
        {"name": "Teams", "description": "Team data operations"},
        {"name": "Events", "description": "Event/game data operations"},
        {"name": "Ingest", "description": "ESPN data ingestion endpoints"},
        {"name": "Health", "description": "Health check endpoints"},
    ],
}


# CORS settings
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=False)


# Cache settings
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}


# Celery settings
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_BEAT_SCHEDULE = {
    # Scoreboards — high-frequency during seasons
    "refresh-nba-scoreboard-hourly": {
        "task": "apps.ingest.tasks.refresh_scoreboard_task",
        "schedule": 3600.0,  # Every hour
        "args": ("basketball", "nba"),
    },
    "refresh-nfl-scoreboard-hourly": {
        "task": "apps.ingest.tasks.refresh_scoreboard_task",
        "schedule": 3600.0,  # Every hour
        "args": ("football", "nfl"),
    },
    # Teams — refreshed weekly (rosters/logos change infrequently)
    "refresh-teams-weekly": {
        "task": "apps.ingest.tasks.refresh_all_teams_task",
        "schedule": 86400.0 * 7,  # Weekly
    },
    # News — ingested every 30 minutes across all leagues
    "refresh-all-news-30min": {
        "task": "apps.ingest.tasks.refresh_all_news_task",
        "schedule": 1800.0,  # Every 30 minutes
    },
    # Injuries — refreshed every 4 hours (snapshot replacement)
    "refresh-all-injuries-4h": {
        "task": "apps.ingest.tasks.refresh_all_injuries_task",
        "schedule": 14400.0,  # Every 4 hours
    },
    # Transactions — refreshed every 6 hours
    "refresh-all-transactions-6h": {
        "task": "apps.ingest.tasks.refresh_all_transactions_task",
        "schedule": 21600.0,  # Every 6 hours
    },
}


# ESPN Client settings
ESPN_CLIENT = {
    # Domain URLs — override in .env if needed
    "SITE_API_BASE_URL": env(
        "ESPN_SITE_API_BASE_URL", default="https://site.api.espn.com"
    ),
    "CORE_API_BASE_URL": env(
        "ESPN_CORE_API_BASE_URL", default="https://sports.core.api.espn.com"
    ),
    "WEB_V3_API_BASE_URL": env(
        "ESPN_WEB_V3_API_BASE_URL", default="https://site.web.api.espn.com"
    ),
    "CDN_API_BASE_URL": env(
        "ESPN_CDN_API_BASE_URL", default="https://cdn.espn.com"
    ),
    "NOW_API_BASE_URL": env(
        "ESPN_NOW_API_BASE_URL", default="https://now.core.api.espn.com"
    ),
    # Request behaviour
    "TIMEOUT": env.float("ESPN_TIMEOUT", default=30.0),
    "MAX_RETRIES": env.int("ESPN_MAX_RETRIES", default=3),
    "RETRY_BACKOFF": env.float("ESPN_RETRY_BACKOFF", default=1.0),
    "USER_AGENT": env(
        "ESPN_USER_AGENT",
        default="ESPN-Service/1.0 (https://github.com/espn-service)",
    ),
    "RATE_LIMIT_REQUESTS": env.int("ESPN_RATE_LIMIT_REQUESTS", default=60),
    "RATE_LIMIT_PERIOD": env.int("ESPN_RATE_LIMIT_PERIOD", default=60),
}


# Structured logging configuration
LOGGING_LEVEL = env("LOGGING_LEVEL", default="INFO")

timestamper = structlog.processors.TimeStamper(fmt="iso")

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.processors.JSONRenderer(),
            "foreign_pre_chain": [
                structlog.contextvars.merge_contextvars,
                structlog.stdlib.add_log_level,
                structlog.stdlib.add_logger_name,
                timestamper,
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
            ],
        },
        "console": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.dev.ConsoleRenderer(),
            "foreign_pre_chain": [
                structlog.contextvars.merge_contextvars,
                structlog.stdlib.add_log_level,
                structlog.stdlib.add_logger_name,
                timestamper,
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
            ],
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
        },
        "json": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOGGING_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": LOGGING_LEVEL,
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": LOGGING_LEVEL,
            "propagate": False,
        },
        "clients": {
            "handlers": ["console"],
            "level": LOGGING_LEVEL,
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": LOGGING_LEVEL,
            "propagate": False,
        },
    },
}

```

---

# FILE: `espn_service/config/settings/local.py`

```python
"""Local development settings."""

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# Database - SQLite for local development
DATABASES = {
    "default": env.db("DATABASE_URL", default="sqlite:///db.sqlite3"),  # noqa: F405
}

# CORS - Allow all in development
CORS_ALLOW_ALL_ORIGINS = True

# Cache - Local memory cache for development
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Add browsable API renderer in development
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]

# Logging - Console output with colors
LOGGING["handlers"]["console"]["formatter"] = "console"  # noqa: F405
LOGGING["root"]["level"] = "DEBUG"  # noqa: F405

# Email - Console backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Celery - Use Redis if available, otherwise use eager mode
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=True)  # noqa: F405

```

---

# FILE: `espn_service/config/settings/production.py`

```python
"""Production settings."""

from .base import *  # noqa: F401, F403

DEBUG = False

# Security settings
SECRET_KEY = env("SECRET_KEY")  # noqa: F405
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")  # noqa: F405

# HTTPS settings
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Database - PostgreSQL required
DATABASES = {
    "default": env.db("DATABASE_URL"),  # noqa: F405
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DATABASE_CONN_MAX_AGE", default=60)  # noqa: F405
DATABASES["default"]["OPTIONS"] = {
    "connect_timeout": 10,
}

# Cache - Redis required
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://redis:6379/1"),  # noqa: F405
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "RETRY_ON_TIMEOUT": True,
        },
    }
}

# Logging - JSON format for production
LOGGING["handlers"]["console"]["formatter"] = "json"  # noqa: F405
LOGGING["root"]["level"] = "INFO"  # noqa: F405
for logger in LOGGING["loggers"].values():  # noqa: F405
    logger["handlers"] = ["json"]

# CORS - Restrict to allowed origins
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])  # noqa: F405

# Celery
CELERY_TASK_ALWAYS_EAGER = False
CELERY_BROKER_URL = env("CELERY_BROKER_URL")  # noqa: F405
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND")  # noqa: F405

# Static files
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Email - Use SMTP in production
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="")  # noqa: F405
EMAIL_PORT = env.int("EMAIL_PORT", default=587)  # noqa: F405
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")  # noqa: F405
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")  # noqa: F405

# Sentry integration (optional)
SENTRY_DSN = env("SENTRY_DSN", default="")  # noqa: F405
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
        ],
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.1),  # noqa: F405
        send_default_pii=False,
        environment=env("ENVIRONMENT", default="production"),  # noqa: F405
    )

```

---

# FILE: `espn_service/config/settings/test.py`

```python
"""Test settings."""

from .base import *  # noqa: F401, F403

DEBUG = False

# Use in-memory SQLite for faster tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Disable password hashing for faster tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Cache - Use dummy cache for tests
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

# Celery - Always eager for tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Logging - Reduce noise during tests
LOGGING["root"]["level"] = "WARNING"  # noqa: F405
for logger in LOGGING["loggers"].values():  # noqa: F405
    logger["level"] = "WARNING"

# Faster static files handling
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# ESPN Client - Use test configuration
ESPN_CLIENT = {
    "SITE_API_BASE_URL": "https://site.api.espn.com",
    "CORE_API_BASE_URL": "https://sports.core.api.espn.com",
    "TIMEOUT": 5.0,
    "MAX_RETRIES": 1,
    "RETRY_BACKOFF": 0.1,
    "USER_AGENT": "ESPN-Service-Test/1.0",
    "RATE_LIMIT_REQUESTS": 1000,
    "RATE_LIMIT_PERIOD": 60,
}

```

---

# FILE: `espn_service/config/urls.py`

```python
"""URL configuration for espn_service project."""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.core.views import HealthCheckView

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # Health check
    path("healthz", HealthCheckView.as_view(), name="health-check"),
    # API v1
    path("api/v1/", include("apps.espn.urls")),
    path("api/v1/ingest/", include("apps.ingest.urls")),
    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

```

---

# FILE: `espn_service/config/wsgi.py`

```python
"""WSGI config for espn_service project."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

application = get_wsgi_application()

```

---

# FILE: `espn_service/conftest.py`

```python
"""Root conftest for pytest - imports from tests package."""

# Re-export all fixtures from tests.conftest
from tests.conftest import *  # noqa: F401, F403

```

---

# FILE: `espn_service/docker-compose.prod.yml`

```yaml
version: '3.8'

services:
  web:
    build:
      context: .
      target: production
    ports:
      - "8000:8000"
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.production
      - DATABASE_URL=${DATABASE_URL}
      - CELERY_BROKER_URL=${CELERY_BROKER_URL}
      - CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND}
      - SECRET_KEY=${SECRET_KEY}
      - ALLOWED_HOSTS=${ALLOWED_HOSTS}
      - CORS_ALLOWED_ORIGINS=${CORS_ALLOWED_ORIGINS:-}
      - SENTRY_DSN=${SENTRY_DSN:-}
    depends_on:
      - redis
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M

  celery:
    build:
      context: .
      target: production
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.production
      - DATABASE_URL=${DATABASE_URL}
      - CELERY_BROKER_URL=${CELERY_BROKER_URL}
      - CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND}
      - SECRET_KEY=${SECRET_KEY}
      - SENTRY_DSN=${SENTRY_DSN:-}
    depends_on:
      - redis
    restart: unless-stopped
    command: celery -A config worker -l INFO --concurrency=2
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M

  celery-beat:
    build:
      context: .
      target: production
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.production
      - DATABASE_URL=${DATABASE_URL}
      - CELERY_BROKER_URL=${CELERY_BROKER_URL}
      - CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND}
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - redis
      - celery
    restart: unless-stopped
    command: celery -A config beat -l INFO
    deploy:
      resources:
        limits:
          cpus: '0.25'
          memory: 128M

volumes:
  redis_data:

```

---

# FILE: `espn_service/docker-compose.test.yml`

```yaml
# docker-compose.test.yml — run tests inside Docker with a fresh Postgres
# Usage:
#   docker compose -f docker-compose.test.yml run --rm test
#   docker compose -f docker-compose.test.yml run --rm test python manage.py makemigrations --check

version: '3.8'

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: espn_test
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d espn_test"]
      interval: 5s
      timeout: 5s
      retries: 10

  test:
    build:
      context: .
      target: production
    working_dir: /app
    volumes:
      - .:/app
    environment:
      DJANGO_SETTINGS_MODULE: config.settings.test
      DATABASE_URL: postgres://postgres:postgres@db:5432/espn_test
      SECRET_KEY: docker-test-secret-key-not-for-production
      DEBUG: "False"
      CELERY_BROKER_URL: ""
    depends_on:
      db:
        condition: service_healthy
    # Default: migrate then run the full test suite
    command: >
      sh -c "python manage.py makemigrations --check --settings=config.settings.test &&
             python manage.py migrate --settings=config.settings.test &&
             python -m pytest tests/ --no-cov -q"

```

---

# FILE: `espn_service/docker-compose.yml`

```yaml
version: '3.8'

services:
  web:
    build:
      context: .
      target: production
    ports:
      - "8000:8000"
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.local
      - DATABASE_URL=postgres://espn:espn@db:5432/espn_service
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - SECRET_KEY=dev-secret-key-change-in-production
      - DEBUG=True
      - ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - .:/app
    command: >
      sh -c "python manage.py migrate &&
             python manage.py runserver 0.0.0.0:8000"

  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=espn
      - POSTGRES_PASSWORD=espn
      - POSTGRES_DB=espn_service
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U espn -d espn_service"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  celery:
    build:
      context: .
      target: production
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.local
      - DATABASE_URL=postgres://espn:espn@db:5432/espn_service
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - SECRET_KEY=dev-secret-key-change-in-production
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - .:/app
    command: celery -A config worker -l INFO

  celery-beat:
    build:
      context: .
      target: production
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.local
      - DATABASE_URL=postgres://espn:espn@db:5432/espn_service
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - SECRET_KEY=dev-secret-key-change-in-production
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      celery:
        condition: service_started
    volumes:
      - .:/app
    command: celery -A config beat -l INFO

volumes:
  postgres_data:
  redis_data:

```

---

# FILE: `espn_service/manage.py`

```python
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

```

---

# FILE: `espn_service/pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "espn-service"
version = "1.0.0"
description = "Production-ready Django REST API for ESPN sports data"
readme = "README.md"
requires-python = ">=3.12"
license = {text = "MIT"}
authors = [
    {name = "ESPN Service Team", email = "team@espn-service.local"}
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Framework :: Django :: 5.0",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    "django>=5.0,<6.0",
    "djangorestframework>=3.14,<4.0",
    "django-environ>=0.11,<1.0",
    "django-cors-headers>=4.3,<5.0",
    "django-filter>=24.0,<25.0",
    "drf-spectacular>=0.27,<1.0",
    "psycopg[binary]>=3.1,<4.0",
    "redis>=5.0,<6.0",
    "django-redis>=5.4,<6.0",
    "celery[redis]>=5.3,<6.0",
    "httpx>=0.27,<1.0",
    "tenacity>=8.2,<9.0",
    "structlog>=24.0,<25.0",
    "gunicorn>=21.0,<23.0",
    "whitenoise>=6.6,<7.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0,<9.0",
    "pytest-django>=4.8,<5.0",
    "pytest-cov>=4.1,<6.0",
    "pytest-asyncio>=0.23,<1.0",
    "pytest-httpx>=0.30,<1.0",
    "factory-boy>=3.3,<4.0",
    "faker>=24.0,<25.0",
    "ruff>=0.3,<1.0",
    "mypy>=1.9,<2.0",
    "django-stubs>=4.2,<6.0",
    "djangorestframework-stubs>=3.14,<4.0",
    "pre-commit>=3.6,<4.0",
    "ipython>=8.22,<9.0",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["config*", "apps*", "clients*"]

[tool.ruff]
target-version = "py312"
line-length = 100
exclude = [
    ".git",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "__pycache__",
    "migrations",
]

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # Pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
    "ARG",    # flake8-unused-arguments
    "SIM",    # flake8-simplify
]
ignore = [
    "E501",   # line too long (handled by formatter)
    "B008",   # do not perform function calls in argument defaults
    "ARG001", # unused function argument
]

[tool.ruff.lint.per-file-ignores]
"tests/*" = [
    "ARG002",  # pytest fixtures must match by name even if unused
    "B017",    # blind Exception catch is acceptable in test integrity checks
]
"apps/ingest/management/commands/*" = [
    "ARG002",  # Django management command handle() signature is fixed
]

[tool.ruff.lint.isort]
known-first-party = ["config", "apps", "clients"]

[tool.mypy]
python_version = "3.12"
plugins = [
    "mypy_django_plugin.main",
    "mypy_drf_plugin.main",
]
strict = true
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = "*.migrations.*"
ignore_errors = true

[tool.django-stubs]
django_settings_module = "config.settings.local"

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.test"
python_files = ["test_*.py", "*_test.py"]
addopts = [
    "--strict-markers",
    "-ra",
    "-q",
    "--cov=apps",
    "--cov=clients",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-fail-under=80",
]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
]

[tool.coverage.run]
branch = true
source = ["apps", "clients"]
omit = [
    "*/migrations/*",
    "*/tests/*",
    "*/__pycache__/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
]

```

---

# FILE: `espn_service/tests/__init__.py`

```python
# Tests package

```

---

# FILE: `espn_service/tests/conftest.py`

```python
"""Pytest configuration and fixtures."""

from datetime import UTC

import pytest
from rest_framework.test import APIClient

from apps.espn.models import Competitor, Event, League, Sport, Team, Venue


@pytest.fixture
def api_client() -> APIClient:
    """Return a DRF API client."""
    return APIClient()


@pytest.fixture
def sport(db) -> Sport:
    """Create a test sport."""
    return Sport.objects.create(slug="basketball", name="Basketball")


@pytest.fixture
def league(db, sport: Sport) -> League:
    """Create a test league."""
    return League.objects.create(
        sport=sport,
        slug="nba",
        name="NBA",
        abbreviation="NBA",
    )


@pytest.fixture
def venue(db) -> Venue:
    """Create a test venue."""
    return Venue.objects.create(
        espn_id="1234",
        name="Test Arena",
        city="Test City",
        state="TS",
        country="USA",
        is_indoor=True,
        capacity=20000,
    )


@pytest.fixture
def team(db, league: League) -> Team:
    """Create a test team."""
    return Team.objects.create(
        league=league,
        espn_id="1",
        uid="s:40~l:46~t:1",
        slug="test-team",
        abbreviation="TST",
        display_name="Test Team",
        short_display_name="Test",
        name="Team",
        nickname="Test City",
        location="Test City",
        color="FF0000",
        alternate_color="0000FF",
        is_active=True,
        logos=[{"href": "https://example.com/logo.png", "rel": ["default"]}],
    )


@pytest.fixture
def team2(db, league: League) -> Team:
    """Create a second test team."""
    return Team.objects.create(
        league=league,
        espn_id="2",
        uid="s:40~l:46~t:2",
        slug="opponent-team",
        abbreviation="OPP",
        display_name="Opponent Team",
        short_display_name="Opponent",
        name="Opponent",
        nickname="Opponent City",
        location="Opponent City",
        color="00FF00",
        is_active=True,
    )


@pytest.fixture
def event(db, league: League, venue: Venue) -> Event:
    """Create a test event."""
    from datetime import datetime

    return Event.objects.create(
        league=league,
        venue=venue,
        espn_id="401584666",
        uid="s:40~l:46~e:401584666",
        date=datetime(2024, 12, 15, 19, 30, tzinfo=UTC),
        name="Test Team at Opponent Team",
        short_name="TST @ OPP",
        season_year=2024,
        season_type=2,
        status=Event.STATUS_FINAL,
        status_detail="Final",
    )


@pytest.fixture
def competitor_home(db, event: Event, team: Team) -> Competitor:
    """Create home competitor."""
    return Competitor.objects.create(
        event=event,
        team=team,
        home_away=Competitor.HOME,
        score="110",
        winner=True,
        order=1,
    )


@pytest.fixture
def competitor_away(db, event: Event, team2: Team) -> Competitor:
    """Create away competitor."""
    return Competitor.objects.create(
        event=event,
        team=team2,
        home_away=Competitor.AWAY,
        score="105",
        winner=False,
        order=0,
    )


# ESPN API mock response fixtures


@pytest.fixture
def mock_teams_response() -> dict:
    """Mock ESPN teams API response."""
    return {
        "sports": [
            {
                "id": "40",
                "name": "Basketball",
                "slug": "basketball",
                "leagues": [
                    {
                        "id": "46",
                        "name": "NBA",
                        "slug": "nba",
                        "teams": [
                            {
                                "team": {
                                    "id": "1",
                                    "uid": "s:40~l:46~t:1",
                                    "slug": "atlanta-hawks",
                                    "abbreviation": "ATL",
                                    "displayName": "Atlanta Hawks",
                                    "shortDisplayName": "Hawks",
                                    "name": "Hawks",
                                    "nickname": "Atlanta",
                                    "location": "Atlanta",
                                    "color": "c8102e",
                                    "alternateColor": "fdb927",
                                    "isActive": True,
                                    "isAllStar": False,
                                    "logos": [
                                        {
                                            "href": "https://a.espncdn.com/i/teamlogos/nba/500/atl.png",
                                            "rel": ["full", "default"],
                                            "width": 500,
                                            "height": 500,
                                        }
                                    ],
                                    "links": [],
                                }
                            },
                            {
                                "team": {
                                    "id": "2",
                                    "uid": "s:40~l:46~t:2",
                                    "slug": "boston-celtics",
                                    "abbreviation": "BOS",
                                    "displayName": "Boston Celtics",
                                    "shortDisplayName": "Celtics",
                                    "name": "Celtics",
                                    "nickname": "Boston",
                                    "location": "Boston",
                                    "color": "007a33",
                                    "alternateColor": "ba9653",
                                    "isActive": True,
                                    "isAllStar": False,
                                    "logos": [],
                                    "links": [],
                                }
                            },
                        ],
                    }
                ],
            }
        ]
    }


@pytest.fixture
def mock_scoreboard_response() -> dict:
    """Mock ESPN scoreboard API response."""
    return {
        "leagues": [
            {
                "id": "46",
                "name": "NBA",
                "abbreviation": "NBA",
            }
        ],
        "events": [
            {
                "id": "401584666",
                "uid": "s:40~l:46~e:401584666",
                "date": "2024-12-15T19:30:00Z",
                "name": "Atlanta Hawks at Boston Celtics",
                "shortName": "ATL @ BOS",
                "season": {
                    "year": 2024,
                    "type": 2,
                    "slug": "regular-season",
                },
                "status": {
                    "type": {
                        "id": "3",
                        "state": "post",
                        "completed": True,
                        "description": "Final",
                        "detail": "Final",
                    },
                    "displayClock": "0:00",
                    "period": 4,
                },
                "competitions": [
                    {
                        "id": "401584666",
                        "attendance": 19156,
                        "venue": {
                            "id": "123",
                            "fullName": "TD Garden",
                            "address": {
                                "city": "Boston",
                                "state": "MA",
                                "country": "USA",
                            },
                            "indoor": True,
                            "capacity": 19580,
                        },
                        "competitors": [
                            {
                                "id": "2",
                                "homeAway": "home",
                                "winner": True,
                                "team": {
                                    "id": "2",
                                    "abbreviation": "BOS",
                                    "displayName": "Boston Celtics",
                                    "name": "Celtics",
                                    "location": "Boston",
                                },
                                "score": "115",
                                "linescores": [
                                    {"value": 28},
                                    {"value": 30},
                                    {"value": 27},
                                    {"value": 30},
                                ],
                                "records": [
                                    {"type": "total", "summary": "20-5"},
                                ],
                            },
                            {
                                "id": "1",
                                "homeAway": "away",
                                "winner": False,
                                "team": {
                                    "id": "1",
                                    "abbreviation": "ATL",
                                    "displayName": "Atlanta Hawks",
                                    "name": "Hawks",
                                    "location": "Atlanta",
                                },
                                "score": "108",
                                "linescores": [
                                    {"value": 25},
                                    {"value": 28},
                                    {"value": 30},
                                    {"value": 25},
                                ],
                                "records": [
                                    {"type": "total", "summary": "15-10"},
                                ],
                            },
                        ],
                        "broadcasts": [
                            {
                                "market": "national",
                                "names": ["ESPN"],
                            }
                        ],
                    }
                ],
                "links": [],
            }
        ],
    }

```

---

# FILE: `espn_service/tests/test_api.py`

```python
"""Tests for REST API endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.espn.models import Competitor, Event, League, Sport, Team
from clients.espn_client import ESPNResponse


@pytest.mark.django_db
class TestHealthCheckEndpoint:
    """Tests for health check endpoint."""

    def test_health_check_success(self, api_client: APIClient):
        """Test health check returns healthy status."""
        response = api_client.get("/healthz")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "healthy"
        assert response.json()["database"] == "connected"


@pytest.mark.django_db
class TestTeamEndpoints:
    """Tests for team API endpoints."""

    def test_list_teams_empty(self, api_client: APIClient, league: League):
        """Test listing teams when none exist."""
        response = api_client.get("/api/v1/teams/")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 0
        assert response.json()["results"] == []

    def test_list_teams(self, api_client: APIClient, team: Team):
        """Test listing teams."""
        response = api_client.get("/api/v1/teams/")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1
        result = response.json()["results"][0]
        assert result["espn_id"] == "1"
        assert result["abbreviation"] == "TST"
        assert result["display_name"] == "Test Team"

    def test_list_teams_filter_by_league(
        self, api_client: APIClient, team: Team, league: League
    ):
        """Test filtering teams by league."""
        response = api_client.get("/api/v1/teams/", {"league": "nba"})

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1

        response = api_client.get("/api/v1/teams/", {"league": "nfl"})
        assert response.json()["count"] == 0

    def test_list_teams_filter_by_sport(
        self, api_client: APIClient, team: Team, sport: Sport
    ):
        """Test filtering teams by sport."""
        response = api_client.get("/api/v1/teams/", {"sport": "basketball"})

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1

        response = api_client.get("/api/v1/teams/", {"sport": "football"})
        assert response.json()["count"] == 0

    def test_list_teams_search(self, api_client: APIClient, team: Team):
        """Test searching teams."""
        response = api_client.get("/api/v1/teams/", {"search": "Test"})

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1

        response = api_client.get("/api/v1/teams/", {"search": "NonExistent"})
        assert response.json()["count"] == 0

    def test_get_team_detail(self, api_client: APIClient, team: Team):
        """Test getting team details."""
        response = api_client.get(f"/api/v1/teams/{team.id}/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["espn_id"] == "1"
        assert data["abbreviation"] == "TST"
        assert data["display_name"] == "Test Team"
        assert data["league"]["slug"] == "nba"
        assert data["primary_logo"] == "https://example.com/logo.png"

    def test_get_team_by_espn_id(self, api_client: APIClient, team: Team):
        """Test getting team by ESPN ID."""
        response = api_client.get("/api/v1/teams/espn/1/")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["espn_id"] == "1"

    def test_get_team_by_espn_id_not_found(self, api_client: APIClient, league: League):
        """Test getting non-existent team by ESPN ID."""
        response = api_client.get("/api/v1/teams/espn/999/")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_team_not_found(self, api_client: APIClient, league: League):
        """Test getting non-existent team."""
        response = api_client.get("/api/v1/teams/999/")

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestEventEndpoints:
    """Tests for event API endpoints."""

    def test_list_events_empty(self, api_client: APIClient, league: League):
        """Test listing events when none exist."""
        response = api_client.get("/api/v1/events/")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 0

    def test_list_events(
        self,
        api_client: APIClient,
        event: Event,
        competitor_home: Competitor,
        competitor_away: Competitor,
    ):
        """Test listing events."""
        response = api_client.get("/api/v1/events/")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1
        result = response.json()["results"][0]
        assert result["espn_id"] == "401584666"
        assert result["short_name"] == "TST @ OPP"
        assert len(result["competitors"]) == 2

    def test_list_events_filter_by_league(
        self, api_client: APIClient, event: Event, league: League
    ):
        """Test filtering events by league."""
        response = api_client.get("/api/v1/events/", {"league": "nba"})

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1

        response = api_client.get("/api/v1/events/", {"league": "nfl"})
        assert response.json()["count"] == 0

    def test_list_events_filter_by_date(self, api_client: APIClient, event: Event):
        """Test filtering events by date."""
        response = api_client.get("/api/v1/events/", {"date": "2024-12-15"})

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1

        response = api_client.get("/api/v1/events/", {"date": "2024-12-16"})
        assert response.json()["count"] == 0

    def test_list_events_filter_by_date_range(self, api_client: APIClient, event: Event):
        """Test filtering events by date range."""
        response = api_client.get(
            "/api/v1/events/",
            {"date_from": "2024-12-14", "date_to": "2024-12-16"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1

    def test_list_events_filter_by_status(self, api_client: APIClient, event: Event):
        """Test filtering events by status."""
        response = api_client.get("/api/v1/events/", {"status": "final"})

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1

        response = api_client.get("/api/v1/events/", {"status": "scheduled"})
        assert response.json()["count"] == 0

    def test_list_events_filter_by_team(
        self,
        api_client: APIClient,
        event: Event,
        competitor_home: Competitor,
        team: Team,
    ):
        """Test filtering events by team."""
        response = api_client.get("/api/v1/events/", {"team": "TST"})

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1

        response = api_client.get("/api/v1/events/", {"team": "XYZ"})
        assert response.json()["count"] == 0

    def test_get_event_detail(
        self,
        api_client: APIClient,
        event: Event,
        competitor_home: Competitor,
        competitor_away: Competitor,
    ):
        """Test getting event details."""
        response = api_client.get(f"/api/v1/events/{event.id}/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["espn_id"] == "401584666"
        assert data["name"] == "Test Team at Opponent Team"
        assert data["status"] == "final"
        assert data["league"]["slug"] == "nba"
        assert data["venue"]["name"] == "Test Arena"
        assert len(data["competitors"]) == 2

    def test_get_event_by_espn_id(self, api_client: APIClient, event: Event):
        """Test getting event by ESPN ID."""
        response = api_client.get("/api/v1/events/espn/401584666/")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["espn_id"] == "401584666"

    def test_get_event_by_espn_id_not_found(self, api_client: APIClient, league: League):
        """Test getting non-existent event by ESPN ID."""
        response = api_client.get("/api/v1/events/espn/999999/")

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestIngestEndpoints:
    """Tests for ingestion API endpoints."""

    def test_ingest_teams_success(
        self, api_client: APIClient, mock_teams_response: dict
    ):
        """Test successful teams ingestion."""
        with patch("apps.ingest.services.get_espn_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_teams.return_value = ESPNResponse(
                data=mock_teams_response,
                status_code=200,
                url="test",
            )
            mock_get_client.return_value = mock_client

            response = api_client.post(
                "/api/v1/ingest/teams/",
                {"sport": "basketball", "league": "nba"},
                format="json",
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["created"] == 2
        assert data["total_processed"] == 2

    def test_ingest_teams_validation_error(self, api_client: APIClient):
        """Test teams ingestion with invalid data."""
        response = api_client.post(
            "/api/v1/ingest/teams/",
            {"league": "nba"},  # Missing sport
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_ingest_scoreboard_success(
        self, api_client: APIClient, mock_scoreboard_response: dict
    ):
        """Test successful scoreboard ingestion."""
        with patch("apps.ingest.services.get_espn_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_scoreboard.return_value = ESPNResponse(
                data=mock_scoreboard_response,
                status_code=200,
                url="test",
            )
            mock_get_client.return_value = mock_client

            response = api_client.post(
                "/api/v1/ingest/scoreboard/",
                {"sport": "basketball", "league": "nba", "date": "20241215"},
                format="json",
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["created"] == 1

    def test_ingest_scoreboard_invalid_date(self, api_client: APIClient):
        """Test scoreboard ingestion with invalid date format."""
        response = api_client.post(
            "/api/v1/ingest/scoreboard/",
            {"sport": "basketball", "league": "nba", "date": "2024-12-15"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_ingest_scoreboard_without_date(
        self, api_client: APIClient, mock_scoreboard_response: dict
    ):
        """Test scoreboard ingestion without date (defaults to today)."""
        with patch("apps.ingest.services.get_espn_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_scoreboard.return_value = ESPNResponse(
                data=mock_scoreboard_response,
                status_code=200,
                url="test",
            )
            mock_get_client.return_value = mock_client

            response = api_client.post(
                "/api/v1/ingest/scoreboard/",
                {"sport": "basketball", "league": "nba"},
                format="json",
            )

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestPagination:
    """Tests for API pagination."""

    def test_teams_pagination(self, api_client: APIClient, league: League):
        """Test teams endpoint pagination."""
        # Create multiple teams
        for i in range(30):
            Team.objects.create(
                league=league,
                espn_id=str(i),
                abbreviation=f"T{i:02d}",
                display_name=f"Team {i}",
            )

        response = api_client.get("/api/v1/teams/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["count"] == 30
        assert len(data["results"]) == 25  # Default page size
        assert data["next"] is not None
        assert data["previous"] is None

        # Get second page
        response = api_client.get("/api/v1/teams/", {"page": 2})
        data = response.json()
        assert len(data["results"]) == 5
        assert data["next"] is None
        assert data["previous"] is not None


@pytest.mark.django_db
class TestSportEndpoints:
    """Tests for sport discovery endpoints."""

    def test_list_sports_empty(self, api_client: APIClient):
        """Test listing sports when none exist."""
        response = api_client.get("/api/v1/sports/")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 0

    def test_list_sports(self, api_client: APIClient, sport: Sport):
        """Test listing sports returns ingested sports."""
        response = api_client.get("/api/v1/sports/")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1
        result = response.json()["results"][0]
        assert result["slug"] == "basketball"
        assert result["name"] == "Basketball"

    def test_get_sport_by_slug(self, api_client: APIClient, sport: Sport):
        """Test retrieving a sport by its slug."""
        response = api_client.get("/api/v1/sports/basketball/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["slug"] == "basketball"
        assert data["name"] == "Basketball"

    def test_get_sport_not_found(self, api_client: APIClient):
        """Test retrieving a non-existent sport returns 404."""
        response = api_client.get("/api/v1/sports/nonexistent/")

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestLeagueEndpoints:
    """Tests for league discovery endpoints."""

    def test_list_leagues_empty(self, api_client: APIClient):
        """Test listing leagues when none exist."""
        response = api_client.get("/api/v1/leagues/")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 0

    def test_list_leagues(self, api_client: APIClient, league: League):
        """Test listing leagues returns ingested leagues."""
        response = api_client.get("/api/v1/leagues/")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1
        result = response.json()["results"][0]
        assert result["slug"] == "nba"
        assert result["abbreviation"] == "NBA"
        assert result["sport"]["slug"] == "basketball"

    def test_list_leagues_filter_by_sport(
        self, api_client: APIClient, league: League
    ):
        """Test filtering leagues by sport slug."""
        response = api_client.get("/api/v1/leagues/", {"sport": "basketball"})

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1

        response = api_client.get("/api/v1/leagues/", {"sport": "football"})
        assert response.json()["count"] == 0

    def test_get_league_detail(self, api_client: APIClient, league: League):
        """Test retrieving a league by ID."""
        response = api_client.get(f"/api/v1/leagues/{league.id}/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["slug"] == "nba"
        assert data["sport"]["slug"] == "basketball"

    def test_get_league_not_found(self, api_client: APIClient):
        """Test retrieving a non-existent league returns 404."""
        response = api_client.get("/api/v1/leagues/999/")

        assert response.status_code == status.HTTP_404_NOT_FOUND

```

---

# FILE: `espn_service/tests/test_espn_client.py`

```python
"""Tests for ESPN client module."""

import httpx
import pytest
from pytest_httpx import HTTPXMock

from apps.core.exceptions import (
    ESPNClientError,
    ESPNNotFoundError,
    ESPNRateLimitError,
)
from clients.espn_client import ESPNClient, ESPNEndpointDomain


class TestESPNClient:
    """Tests for ESPNClient class."""

    def test_client_initialization(self):
        """Test client initializes with default settings."""
        client = ESPNClient()
        assert client.site_api_url == "https://site.api.espn.com"
        assert client.core_api_url == "https://sports.core.api.espn.com"
        assert client.timeout == 5.0  # From test settings
        assert client.max_retries == 1  # From test settings

    def test_client_custom_initialization(self):
        """Test client initializes with custom settings."""
        client = ESPNClient(
            site_api_url="https://custom.api.com",
            timeout=60.0,
            max_retries=5,
        )
        assert client.site_api_url == "https://custom.api.com"
        assert client.timeout == 60.0
        assert client.max_retries == 5

    def test_build_url_site_domain(self):
        """Test URL building for site domain."""
        client = ESPNClient()
        url = client._build_url(
            ESPNEndpointDomain.SITE,
            "/apis/site/v2/sports/basketball/nba/scoreboard",
        )
        assert url == "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"

    def test_build_url_core_domain(self):
        """Test URL building for core domain."""
        client = ESPNClient()
        url = client._build_url(
            ESPNEndpointDomain.CORE,
            "/v2/sports/basketball/leagues/nba",
        )
        assert url == "https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba"

    def test_context_manager(self):
        """Test client can be used as context manager."""
        with ESPNClient() as client:
            assert client._client is None  # Lazy initialization

    def test_get_scoreboard_success(self, httpx_mock: HTTPXMock):
        """Test successful scoreboard fetch."""
        mock_response = {
            "events": [
                {"id": "123", "name": "Test Game"},
            ]
        }
        httpx_mock.add_response(
            url="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=20241215",
            json=mock_response,
        )

        with ESPNClient() as client:
            response = client.get_scoreboard("basketball", "nba", "20241215")

        assert response.is_success
        assert response.data == mock_response

    def test_get_scoreboard_with_datetime(self, httpx_mock: HTTPXMock):
        """Test scoreboard fetch with datetime object."""
        from datetime import datetime

        mock_response = {"events": []}
        httpx_mock.add_response(
            url="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=20241215",
            json=mock_response,
        )

        with ESPNClient() as client:
            response = client.get_scoreboard(
                "basketball",
                "nba",
                datetime(2024, 12, 15),
            )

        assert response.is_success

    def test_get_teams_success(self, httpx_mock: HTTPXMock):
        """Test successful teams fetch."""
        mock_response = {
            "sports": [
                {
                    "leagues": [
                        {
                            "teams": [{"id": "1", "name": "Test Team"}],
                        }
                    ]
                }
            ]
        }
        httpx_mock.add_response(
            url="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams?limit=100",
            json=mock_response,
        )

        with ESPNClient() as client:
            response = client.get_teams("basketball", "nba")

        assert response.is_success
        assert response.data == mock_response

    def test_get_team_success(self, httpx_mock: HTTPXMock):
        """Test successful single team fetch."""
        mock_response = {"team": {"id": "1", "name": "Atlanta Hawks"}}
        httpx_mock.add_response(
            url="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/1",
            json=mock_response,
        )

        with ESPNClient() as client:
            response = client.get_team("basketball", "nba", "1")

        assert response.is_success
        assert response.data["team"]["id"] == "1"

    def test_handle_404_response(self, httpx_mock: HTTPXMock):
        """Test 404 response raises ESPNNotFoundError."""
        httpx_mock.add_response(
            url="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/999",
            status_code=404,
        )

        with ESPNClient() as client, pytest.raises(ESPNNotFoundError):
            client.get_team("basketball", "nba", "999")

    def test_handle_429_response(self, httpx_mock: HTTPXMock):
        """Test 429 response raises ESPNRateLimitError."""
        httpx_mock.add_response(
            url="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
            status_code=429,
        )

        with ESPNClient() as client, pytest.raises(ESPNRateLimitError):
            client.get_scoreboard("basketball", "nba")

    def test_handle_500_response_with_retry(self, httpx_mock: HTTPXMock):
        """Test 500 response triggers retry and eventually raises error."""
        # Add response for the single retry attempt (max_retries=1 in test settings)
        httpx_mock.add_response(
            url="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
            status_code=500,
        )

        with ESPNClient() as client, pytest.raises(ESPNClientError):
            client.get_scoreboard("basketball", "nba")

    def test_handle_invalid_json(self, httpx_mock: HTTPXMock):
        """Test invalid JSON response raises ESPNClientError."""
        httpx_mock.add_response(
            url="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
            content=b"not valid json",
            headers={"content-type": "application/json"},
        )

        with ESPNClient() as client, pytest.raises(ESPNClientError) as exc_info:
            client.get_scoreboard("basketball", "nba")

        assert "Failed to parse" in str(exc_info.value)

    def test_get_event_success(self, httpx_mock: HTTPXMock):
        """Test successful event fetch."""
        mock_response = {"header": {"id": "401584666"}}
        httpx_mock.add_response(
            url="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event=401584666",
            json=mock_response,
        )

        with ESPNClient() as client:
            response = client.get_event("basketball", "nba", "401584666")

        assert response.is_success

    def test_get_league_info_success(self, httpx_mock: HTTPXMock):
        """Test successful league info fetch from core API."""
        mock_response = {"id": "46", "name": "NBA"}
        httpx_mock.add_response(
            url="https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba",
            json=mock_response,
        )

        with ESPNClient() as client:
            response = client.get_league_info("basketball", "nba")

        assert response.is_success
        assert response.data["name"] == "NBA"


class TestESPNClientRetry:
    """Tests for ESPN client retry behavior."""

    def test_retry_on_transport_error(self, httpx_mock: HTTPXMock):
        """Test retry on transport errors."""
        # First request raises error, second succeeds
        httpx_mock.add_exception(
            httpx.ConnectError("Connection refused"),
            url="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
        )

        with ESPNClient() as client, pytest.raises(ESPNClientError) as exc_info:
            client.get_scoreboard("basketball", "nba")

        assert "connection error" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Domain routing — new domains added to ESPNEndpointDomain
# ---------------------------------------------------------------------------

class TestNewDomainRouting:
    """Verify new ESPNEndpointDomain values map to correct base URLs."""

    def setup_method(self):
        self.client = ESPNClient(site_api_url="https://site.api.espn.com")

    def test_web_v3_domain_url(self):
        url = self.client._build_url(
            ESPNEndpointDomain.WEB_V3,
            "/apis/common/v3/sports/basketball/nba/athletes/1/stats",
        )
        assert url.startswith("https://site.web.api.espn.com")

    def test_cdn_domain_url(self):
        url = self.client._build_url(ESPNEndpointDomain.CDN, "/core/nfl/game")
        assert url.startswith("https://cdn.espn.com")

    def test_now_domain_url(self):
        url = self.client._build_url(ESPNEndpointDomain.NOW, "/v1/sports/news")
        assert url.startswith("https://now.core.api.espn.com")


# ---------------------------------------------------------------------------
# get_standings bug-fix regression
# ---------------------------------------------------------------------------

class TestGetStandingsDomainFix:
    """Regression: get_standings must use /apis/v2/ not /apis/site/v2/."""

    def test_standings_path_uses_apis_v2(self, httpx_mock: HTTPXMock):
        """Standings must resolve to /apis/v2/ — not /apis/site/v2/."""
        httpx_mock.add_response(
            url="https://site.api.espn.com/apis/v2/sports/basketball/nba/standings",
            json={"children": [], "seasons": {}},
        )
        with ESPNClient() as client:
            resp = client.get_standings("basketball", "nba")
        assert resp.is_success

    def test_standings_path_does_not_use_site_v2(self):
        """Ensure the path string itself is /apis/v2/, never /apis/site/v2/."""
        client = ESPNClient()
        # Inspect the path string that would be composed
        # get_standings produces: /apis/v2/sports/{sport}/{league}/standings
        from unittest.mock import patch, MagicMock
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.data = {}
        with patch.object(client, "_request_with_retry", return_value=mock_resp) as mock_req:
            client.get_standings("football", "nfl")
        called_url = mock_req.call_args[0][1]
        assert "/apis/v2/sports/football/nfl/standings" in called_url
        assert "/apis/site/v2/" not in called_url


# ---------------------------------------------------------------------------
# League-wide Site API endpoints
# ---------------------------------------------------------------------------

class TestLeagueWideEndpoints:

    def test_get_league_injuries(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries",
            json={"items": []},
        )
        with ESPNClient() as client:
            resp = client.get_league_injuries("basketball", "nba")
        assert resp.is_success

    def test_get_league_transactions(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://site.api.espn.com/apis/site/v2/sports/football/nfl/transactions",
            json={"items": []},
        )
        with ESPNClient() as client:
            resp = client.get_league_transactions("football", "nfl")
        assert resp.is_success

    def test_get_groups(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/groups",
            json={"groups": []},
        )
        with ESPNClient() as client:
            resp = client.get_groups("basketball", "nba")
        assert resp.is_success


# ---------------------------------------------------------------------------
# Athlete common/v3 endpoints
# ---------------------------------------------------------------------------

class TestAthleteV3Endpoints:

    def test_get_athlete_overview_uses_web_domain(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/1234/overview",
            json={"athlete": {}, "statistics": []},
        )
        with ESPNClient() as client:
            resp = client.get_athlete_overview("basketball", "nba", 1234)
        assert resp.is_success

    def test_get_athlete_stats_uses_web_domain(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/3054211/stats",
            json={"filters": [], "athletes": []},
        )
        with ESPNClient() as client:
            resp = client.get_athlete_stats("football", "nfl", 3054211)
        assert resp.is_success

    def test_get_athlete_gamelog_uses_web_domain(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://site.web.api.espn.com/apis/common/v3/sports/baseball/mlb/athletes/33912/gamelog",
            json={"events": []},
        )
        with ESPNClient() as client:
            resp = client.get_athlete_gamelog("baseball", "mlb", 33912)
        assert resp.is_success

    def test_get_athlete_splits_uses_web_domain(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://site.web.api.espn.com/apis/common/v3/sports/hockey/nhl/athletes/999/splits",
            json={"splits": {}},
        )
        with ESPNClient() as client:
            resp = client.get_athlete_splits("hockey", "nhl", 999)
        assert resp.is_success

    def test_get_statistics_by_athlete_uses_web_domain(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://site.web.api.espn.com/apis/common/v3/sports/baseball/mlb/statistics/byathlete?limit=50&page=1&category=batting",
            json={"athletes": []},
        )
        with ESPNClient() as client:
            resp = client.get_statistics_by_athlete("baseball", "mlb", category="batting")
        assert resp.is_success


# ---------------------------------------------------------------------------
# CDN Game Data endpoints
# ---------------------------------------------------------------------------

class TestCDNEndpoints:

    def test_get_cdn_game_uses_cdn_domain(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://cdn.espn.com/core/nfl/game?xhr=1&gameId=401547667",
            json={"gamepackageJSON": {}},
        )
        with ESPNClient() as client:
            resp = client.get_cdn_game("nfl", "401547667")
        assert resp.is_success

    def test_get_cdn_game_boxscore_view(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://cdn.espn.com/core/nba/boxscore?xhr=1&gameId=401584666",
            json={"gamepackageJSON": {}},
        )
        with ESPNClient() as client:
            resp = client.get_cdn_game("nba", "401584666", view="boxscore")
        assert resp.is_success

    def test_get_cdn_scoreboard(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://cdn.espn.com/core/nba/scoreboard?xhr=1",
            json={"events": []},
        )
        with ESPNClient() as client:
            resp = client.get_cdn_scoreboard("nba")
        assert resp.is_success


# ---------------------------------------------------------------------------
# Now/News endpoint
# ---------------------------------------------------------------------------

class TestNowNewsEndpoints:

    def test_get_now_news_uses_now_domain(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://now.core.api.espn.com/v1/sports/news?limit=20&offset=0",
            json={"resultsCount": 0, "feed": []},
        )
        with ESPNClient() as client:
            resp = client.get_now_news()
        assert resp.is_success

    def test_get_now_news_with_sport_filter(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://now.core.api.espn.com/v1/sports/news?limit=20&offset=0&sport=football&league=nfl",
            json={"resultsCount": 5, "feed": []},
        )
        with ESPNClient() as client:
            resp = client.get_now_news(sport="football", league="nfl")
        assert resp.is_success

```

---

# FILE: `espn_service/tests/test_espn_client_new_methods.py`

```python
"""Tests for new ESPN client methods added during March 2026 audit."""

from pytest_httpx import HTTPXMock

from clients.espn_client import ESPNClient


class TestTeamSubResources:
    """Tests for team sub-resource endpoints (injuries, depth charts, transactions)."""

    def test_get_team_injuries(self, httpx_mock: HTTPXMock):
        """Test team injuries endpoint."""
        mock_response = {
            "team": {"id": "9", "abbreviation": "GSW"},
            "injuries": [
                {
                    "id": "1",
                    "athlete": {"id": "3136776", "displayName": "Stephen Curry"},
                    "status": "Doubtful",
                    "location": "left knee",
                }
            ],
        }
        httpx_mock.add_response(
            url="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/9/injuries",
            json=mock_response,
        )

        with ESPNClient() as client:
            response = client.get_team_injuries("basketball", "nba", "9")

        assert response.is_success
        assert response.data["team"]["abbreviation"] == "GSW"
        assert len(response.data["injuries"]) == 1
        assert response.data["injuries"][0]["status"] == "Doubtful"

    def test_get_team_depth_chart(self, httpx_mock: HTTPXMock):
        """Test team depth chart endpoint."""
        mock_response = {
            "team": {"id": "6", "abbreviation": "DAL"},
            "positions": [
                {
                    "position": {"name": "Quarterback", "abbreviation": "QB"},
                    "athletes": [
                        {"rank": 1, "athlete": {"displayName": "Dak Prescott"}},
                        {"rank": 2, "athlete": {"displayName": "Cooper Rush"}},
                    ],
                }
            ],
        }
        httpx_mock.add_response(
            url="https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/6/depthcharts",
            json=mock_response,
        )

        with ESPNClient() as client:
            response = client.get_team_depth_chart("football", "nfl", "6")

        assert response.is_success
        assert response.data["team"]["abbreviation"] == "DAL"
        positions = response.data["positions"]
        assert positions[0]["position"]["abbreviation"] == "QB"
        assert len(positions[0]["athletes"]) == 2

    def test_get_team_transactions(self, httpx_mock: HTTPXMock):
        """Test team transactions endpoint."""
        mock_response = {
            "transactions": [
                {
                    "id": "1",
                    "type": {"text": "Signed"},
                    "athlete": {"displayName": "Test Player"},
                    "date": "2025-03-01",
                }
            ]
        }
        httpx_mock.add_response(
            url="https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/6/transactions",
            json=mock_response,
        )

        with ESPNClient() as client:
            response = client.get_team_transactions("football", "nfl", "6")

        assert response.is_success
        assert len(response.data["transactions"]) == 1
        assert response.data["transactions"][0]["type"]["text"] == "Signed"


class TestGameSituationEndpoints:
    """Tests for game situation sub-resource endpoints."""

    def test_get_game_situation(self, httpx_mock: HTTPXMock):
        """Test game situation endpoint (down, distance, possession)."""
        mock_response = {
            "down": 3,
            "distance": 7,
            "isRedZone": False,
            "possession": {"id": "12", "displayName": "Kansas City Chiefs"},
        }
        url = (
            "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl"
            "/events/401671823/competitions/401671823/situation"
        )
        httpx_mock.add_response(url=url, json=mock_response)

        with ESPNClient() as client:
            response = client.get_game_situation("football", "nfl", "401671823")

        assert response.is_success
        assert response.data["down"] == 3
        assert response.data["distance"] == 7

    def test_get_game_predictor(self, httpx_mock: HTTPXMock):
        """Test ESPN game predictor endpoint."""
        mock_response = {
            "header": "ESPN BPI Win Probability",
            "homeTeam": {"gameProjection": "63.4"},
            "awayTeam": {"gameProjection": "36.6"},
        }
        url = (
            "https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba"
            "/events/401765432/competitions/401765432/predictor"
        )
        httpx_mock.add_response(url=url, json=mock_response)

        with ESPNClient() as client:
            response = client.get_game_predictor("basketball", "nba", "401765432")

        assert response.is_success
        assert float(response.data["homeTeam"]["gameProjection"]) > 50

    def test_get_game_broadcasts(self, httpx_mock: HTTPXMock):
        """Test game broadcasts endpoint."""
        mock_response = {
            "count": 1,
            "items": [
                {
                    "media": {"shortName": "ESPN"},
                    "market": {"id": "1", "type": "National"},
                }
            ],
        }
        url = (
            "https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba"
            "/events/401765432/competitions/401765432/broadcasts"
        )
        httpx_mock.add_response(url=url, json=mock_response)

        with ESPNClient() as client:
            response = client.get_game_broadcasts("basketball", "nba", "401765432")

        assert response.is_success
        assert response.data["items"][0]["media"]["shortName"] == "ESPN"

    def test_game_endpoints_use_event_id_as_competition_id_default(
        self, httpx_mock: HTTPXMock
    ):
        """Test that competition_id defaults to event_id when not provided."""
        mock_response = {"count": 0, "items": []}
        url = (
            "https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba"
            "/events/99999/competitions/99999/broadcasts"
        )
        httpx_mock.add_response(url=url, json=mock_response)

        with ESPNClient() as client:
            response = client.get_game_broadcasts("basketball", "nba", "99999")

        assert response.is_success


class TestCoachesEndpoints:
    """Tests for coaches endpoints."""

    def test_get_coaches_current_season(self, httpx_mock: HTTPXMock):
        """Test coaches endpoint without season (current season)."""
        mock_response = {
            "count": 30,
            "items": [
                {
                    "id": "6010",
                    "firstName": "Steve",
                    "lastName": "Kerr",
                    "experience": 10,
                }
            ],
        }
        httpx_mock.add_response(
            url="https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/coaches?limit=100",
            json=mock_response,
        )

        with ESPNClient() as client:
            response = client.get_coaches("basketball", "nba")

        assert response.is_success
        assert response.data["count"] == 30
        assert response.data["items"][0]["lastName"] == "Kerr"

    def test_get_coaches_with_season(self, httpx_mock: HTTPXMock):
        """Test coaches endpoint with specific season."""
        mock_response = {"count": 32, "items": []}
        httpx_mock.add_response(
            url="https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/2024/coaches?limit=100",
            json=mock_response,
        )

        with ESPNClient() as client:
            response = client.get_coaches("football", "nfl", season=2024)

        assert response.is_success

    def test_get_coach_by_id(self, httpx_mock: HTTPXMock):
        """Test single coach profile endpoint."""
        mock_response = {
            "id": "6010",
            "firstName": "Steve",
            "lastName": "Kerr",
            "experience": 10,
            "record": {"overall": {"wins": 548, "losses": 232}},
        }
        httpx_mock.add_response(
            url="https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/coaches/6010",
            json=mock_response,
        )

        with ESPNClient() as client:
            response = client.get_coach("basketball", "nba", "6010")

        assert response.is_success
        assert response.data["id"] == "6010"
        assert response.data["record"]["overall"]["wins"] == 548


class TestQBREndpoint:
    """Tests for QBR (Quarterback Rating) endpoint."""

    def test_get_qbr_season_totals(self, httpx_mock: HTTPXMock):
        """Test QBR season totals endpoint."""
        mock_response = {
            "leaders": [
                {"athlete": {"displayName": "Patrick Mahomes"}, "value": 82.4}
            ]
        }
        url = (
            "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl"
            "/seasons/2024/types/2/groups/1/qbr/0"
        )
        httpx_mock.add_response(url=url, json=mock_response)

        with ESPNClient() as client:
            response = client.get_qbr(league="nfl", season=2024)

        assert response.is_success
        assert response.data["leaders"][0]["value"] == 82.4

    def test_get_qbr_weekly(self, httpx_mock: HTTPXMock):
        """Test QBR weekly endpoint."""
        mock_response = {"leaders": []}
        url = (
            "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl"
            "/seasons/2024/types/2/weeks/1/qbr/0"
        )
        httpx_mock.add_response(url=url, json=mock_response)

        with ESPNClient() as client:
            response = client.get_qbr(league="nfl", season=2024, week=1)

        assert response.is_success

    def test_get_qbr_home_split(self, httpx_mock: HTTPXMock):
        """Test QBR with home split (split=1)."""
        mock_response = {"leaders": []}
        url = (
            "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl"
            "/seasons/2024/types/2/groups/1/qbr/1"
        )
        httpx_mock.add_response(url=url, json=mock_response)

        with ESPNClient() as client:
            response = client.get_qbr(league="nfl", season=2024, split=1)

        assert response.is_success

    def test_get_qbr_ncaaf(self, httpx_mock: HTTPXMock):
        """Test QBR for College Football (group=80)."""
        mock_response = {"leaders": []}
        url = (
            "https://sports.core.api.espn.com/v2/sports/football/leagues/college-football"
            "/seasons/2024/types/2/groups/80/qbr/0"
        )
        httpx_mock.add_response(url=url, json=mock_response)

        with ESPNClient() as client:
            response = client.get_qbr(
                league="college-football", season=2024, group=80
            )

        assert response.is_success


class TestPowerIndexEndpoint:
    """Tests for Power Index (BPI / SP+) endpoint."""

    def test_get_power_index_league_wide(self, httpx_mock: HTTPXMock):
        """Test power index for whole league."""
        mock_response = {
            "count": 351,
            "items": [{"team": {"id": "99"}, "value": 18.4}],
        }
        url = (
            "https://sports.core.api.espn.com/v2/sports/basketball/leagues"
            "/mens-college-basketball/seasons/2025/powerindex"
        )
        httpx_mock.add_response(url=url, json=mock_response)

        with ESPNClient() as client:
            response = client.get_power_index(
                "basketball", "mens-college-basketball", 2025
            )

        assert response.is_success
        assert response.data["count"] == 351

    def test_get_power_index_single_team(self, httpx_mock: HTTPXMock):
        """Test power index for a specific team."""
        mock_response = {
            "team": {"id": "150", "displayName": "Duke Blue Devils"},
            "value": 21.7,
        }
        url = (
            "https://sports.core.api.espn.com/v2/sports/basketball/leagues"
            "/mens-college-basketball/seasons/2025/powerindex/150"
        )
        httpx_mock.add_response(url=url, json=mock_response)

        with ESPNClient() as client:
            response = client.get_power_index(
                "basketball", "mens-college-basketball", 2025, team_id="150"
            )

        assert response.is_success
        assert response.data["value"] == 21.7

```

---

# FILE: `espn_service/tests/test_ingest_all_teams.py`

```python
"""Tests for the ingest_all_teams management command."""

from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.ingest.services import IngestionResult


@pytest.mark.django_db
class TestIngestAllTeamsCommand:
    """Tests for the ingest_all_teams management command."""

    def _make_result(self, created=1, updated=0, errors=0):
        """Helper to build a mock IngestionResult."""
        result = MagicMock(spec=IngestionResult)
        result.created = created
        result.updated = updated
        result.errors = errors
        return result

    def _call(self, *args, **kwargs):
        """Call the command and capture stdout."""
        out = StringIO()
        call_command("ingest_all_teams", *args, stdout=out, **kwargs)
        return out.getvalue()

    def test_dry_run_lists_leagues(self):
        """Dry run should list leagues without making any API calls."""
        with patch("apps.ingest.services.TeamIngestionService") as mock_svc:
            output = self._call("--dry-run")

        # No API calls
        mock_svc.return_value.ingest_teams.assert_not_called()
        assert "[DRY RUN]" in output
        # Spot-check a known league appears
        assert "basketball/nba" in output or "football/nfl" in output

    def test_dry_run_with_sport_filter(self):
        """Dry run with --sport should list only that sport's leagues."""
        with patch("apps.ingest.services.TeamIngestionService"):
            output = self._call("--dry-run", "--sport", "basketball")

        assert "basketball" in output
        assert "football" not in output

    def test_sport_filter_invalid_raises(self):
        """Unknown --sport should raise CommandError."""
        with pytest.raises(CommandError, match="No leagues configured"):
            self._call("--sport", "not-a-real-sport")

    def test_successful_ingestion(self):
        """Happy path: all leagues ingest successfully."""
        mock_result = self._make_result(created=30, updated=0, errors=0)

        with patch(
            "apps.ingest.management.commands.ingest_all_teams.TeamIngestionService"
        ) as mock_cls:
            mock_cls.return_value.ingest_teams.return_value = mock_result
            output = self._call("--sport", "basketball")

        assert "Done" in output
        # Should have ingested all basketball leagues
        service = mock_cls.return_value
        assert service.ingest_teams.call_count >= 1
        # All calls should be for basketball
        for call_args in service.ingest_teams.call_args_list:
            assert call_args[0][0] == "basketball"

    def test_continue_on_error_default(self):
        """Should continue processing remaining leagues on failure."""
        def side_effect(sport, league):
            if league == "nba":
                raise RuntimeError("API timeout")
            return self._make_result()

        with patch(
            "apps.ingest.management.commands.ingest_all_teams.TeamIngestionService"
        ) as mock_cls:
            mock_cls.return_value.ingest_teams.side_effect = side_effect
            # Should not raise — default is continue-on-error
            output = self._call("--sport", "basketball")

        assert "✗" in output  # error marker in output
        assert "Done" in output  # still completes

    def test_stop_on_error_when_flag_disabled(self):
        """With --continue-on-error=False, should stop at first failure."""
        with patch(
            "apps.ingest.management.commands.ingest_all_teams.TeamIngestionService"
        ) as mock_cls:
            mock_cls.return_value.ingest_teams.side_effect = RuntimeError("fail")

            with pytest.raises((CommandError, SystemExit, RuntimeError)):
                out = StringIO()
                call_command(
                    "ingest_all_teams",
                    "--sport", "basketball",
                    "--continue-on-error",
                    False,
                    stdout=out,
                )

    def test_summary_shows_totals(self):
        """Summary line should aggregate created/updated/error counts."""
        mock_result = self._make_result(created=15, updated=5, errors=0)

        with patch(
            "apps.ingest.management.commands.ingest_all_teams.TeamIngestionService"
        ) as mock_cls:
            mock_cls.return_value.ingest_teams.return_value = mock_result
            output = self._call("--sport", "football")

        # Summary should appear
        assert "Total" in output or "created=" in output

```

---

# FILE: `espn_service/tests/test_ingestion.py`

```python
"""Tests for ingestion services."""

from datetime import UTC
from unittest.mock import MagicMock

import pytest

from apps.espn.models import Competitor, Event, League, Sport, Team
from apps.ingest.services import (
    IngestionResult,
    ScoreboardIngestionService,
    TeamIngestionService,
    get_or_create_sport_and_league,
)
from clients.espn_client import ESPNResponse


@pytest.mark.django_db
class TestGetOrCreateSportAndLeague:
    """Tests for get_or_create_sport_and_league helper."""

    def test_creates_new_sport_and_league(self):
        """Test creating new sport and league."""
        sport, league = get_or_create_sport_and_league("basketball", "nba")

        assert sport.slug == "basketball"
        assert sport.name == "Basketball"
        assert league.slug == "nba"
        # league.name stores the full official name from LEAGUE_INFO
        assert league.name == "National Basketball Association"
        # league.abbreviation stores the short form
        assert league.abbreviation == "NBA"
        assert league.sport == sport

    def test_reuses_existing_sport_and_league(self):
        """Test reusing existing sport and league."""
        sport1, league1 = get_or_create_sport_and_league("basketball", "nba")
        sport2, league2 = get_or_create_sport_and_league("basketball", "nba")

        assert sport1.id == sport2.id
        assert league1.id == league2.id

    def test_creates_different_leagues_for_same_sport(self):
        """Test creating different leagues for same sport."""
        _, nba = get_or_create_sport_and_league("basketball", "nba")
        _, wnba = get_or_create_sport_and_league("basketball", "wnba")

        assert nba.sport == wnba.sport
        assert nba.id != wnba.id


@pytest.mark.django_db
class TestTeamIngestionService:
    """Tests for TeamIngestionService."""

    def test_ingest_teams_success(self, mock_teams_response):
        """Test successful team ingestion."""
        mock_client = MagicMock()
        mock_client.get_teams.return_value = ESPNResponse(
            data=mock_teams_response,
            status_code=200,
            url="test",
        )

        service = TeamIngestionService(client=mock_client)
        result = service.ingest_teams("basketball", "nba")

        assert result.created == 2
        assert result.updated == 0
        assert result.errors == 0

        # Verify teams were created
        assert Team.objects.count() == 2
        atl = Team.objects.get(espn_id="1")
        assert atl.abbreviation == "ATL"
        assert atl.display_name == "Atlanta Hawks"

    def test_ingest_teams_updates_existing(self, mock_teams_response):
        """Test team ingestion updates existing records."""
        # Create sport and league first
        sport = Sport.objects.create(slug="basketball", name="Basketball")
        league = League.objects.create(
            sport=sport, slug="nba", name="NBA", abbreviation="NBA"
        )

        # Create existing team
        Team.objects.create(
            league=league,
            espn_id="1",
            abbreviation="OLD",
            display_name="Old Name",
        )

        mock_client = MagicMock()
        mock_client.get_teams.return_value = ESPNResponse(
            data=mock_teams_response,
            status_code=200,
            url="test",
        )

        service = TeamIngestionService(client=mock_client)
        result = service.ingest_teams("basketball", "nba")

        assert result.created == 1  # BOS is new
        assert result.updated == 1  # ATL is updated

        # Verify team was updated
        atl = Team.objects.get(espn_id="1")
        assert atl.abbreviation == "ATL"
        assert atl.display_name == "Atlanta Hawks"

    def test_ingest_teams_handles_empty_response(self):
        """Test handling empty teams response."""
        mock_client = MagicMock()
        mock_client.get_teams.return_value = ESPNResponse(
            data={"sports": [{"leagues": [{"teams": []}]}]},
            status_code=200,
            url="test",
        )

        service = TeamIngestionService(client=mock_client)
        result = service.ingest_teams("basketball", "nba")

        assert result.created == 0
        assert result.updated == 0


@pytest.mark.django_db
class TestScoreboardIngestionService:
    """Tests for ScoreboardIngestionService."""

    def test_ingest_scoreboard_success(self, mock_scoreboard_response):
        """Test successful scoreboard ingestion."""
        # Pre-create teams
        sport = Sport.objects.create(slug="basketball", name="Basketball")
        league = League.objects.create(
            sport=sport, slug="nba", name="NBA", abbreviation="NBA"
        )
        Team.objects.create(
            league=league, espn_id="1", abbreviation="ATL", display_name="Atlanta Hawks"
        )
        Team.objects.create(
            league=league, espn_id="2", abbreviation="BOS", display_name="Boston Celtics"
        )

        mock_client = MagicMock()
        mock_client.get_scoreboard.return_value = ESPNResponse(
            data=mock_scoreboard_response,
            status_code=200,
            url="test",
        )

        service = ScoreboardIngestionService(client=mock_client)
        result = service.ingest_scoreboard("basketball", "nba", "20241215")

        assert result.created == 1
        assert result.errors == 0

        # Verify event was created
        event = Event.objects.get(espn_id="401584666")
        assert event.name == "Atlanta Hawks at Boston Celtics"
        assert event.short_name == "ATL @ BOS"
        assert event.status == Event.STATUS_FINAL

        # Verify venue was created
        assert event.venue is not None
        assert event.venue.name == "TD Garden"
        assert event.venue.city == "Boston"

        # Verify competitors were created
        assert event.competitors.count() == 2
        home_comp = event.competitors.get(home_away=Competitor.HOME)
        assert home_comp.team.abbreviation == "BOS"
        assert home_comp.score == "115"
        assert home_comp.winner is True

    def test_ingest_scoreboard_creates_missing_teams(self, mock_scoreboard_response):
        """Test scoreboard ingestion creates missing teams."""
        mock_client = MagicMock()
        mock_client.get_scoreboard.return_value = ESPNResponse(
            data=mock_scoreboard_response,
            status_code=200,
            url="test",
        )

        service = ScoreboardIngestionService(client=mock_client)
        result = service.ingest_scoreboard("basketball", "nba", "20241215")

        assert result.created == 1

        # Verify teams were created as side effect
        assert Team.objects.count() == 2

    def test_ingest_scoreboard_updates_existing_event(self, mock_scoreboard_response):
        """Test scoreboard ingestion updates existing events."""
        # Create existing data
        sport = Sport.objects.create(slug="basketball", name="Basketball")
        league = League.objects.create(
            sport=sport, slug="nba", name="NBA", abbreviation="NBA"
        )
        Team.objects.create(
            league=league, espn_id="1", abbreviation="ATL", display_name="Atlanta Hawks"
        )
        Team.objects.create(
            league=league, espn_id="2", abbreviation="BOS", display_name="Boston Celtics"
        )

        from datetime import datetime

        Event.objects.create(
            league=league,
            espn_id="401584666",
            date=datetime(2024, 12, 15, tzinfo=UTC),
            name="Old Name",
            status=Event.STATUS_SCHEDULED,
            season_year=2024,
            season_type=2,
        )

        mock_client = MagicMock()
        mock_client.get_scoreboard.return_value = ESPNResponse(
            data=mock_scoreboard_response,
            status_code=200,
            url="test",
        )

        service = ScoreboardIngestionService(client=mock_client)
        result = service.ingest_scoreboard("basketball", "nba", "20241215")

        assert result.created == 0
        assert result.updated == 1

        # Verify event was updated
        event = Event.objects.get(espn_id="401584666")
        assert event.name == "Atlanta Hawks at Boston Celtics"
        assert event.status == Event.STATUS_FINAL

    def test_ingest_scoreboard_handles_empty_response(self):
        """Test handling empty scoreboard response."""
        mock_client = MagicMock()
        mock_client.get_scoreboard.return_value = ESPNResponse(
            data={"events": []},
            status_code=200,
            url="test",
        )

        service = ScoreboardIngestionService(client=mock_client)
        result = service.ingest_scoreboard("basketball", "nba", "20241215")

        assert result.created == 0
        assert result.updated == 0


class TestIngestionResult:
    """Tests for IngestionResult dataclass."""

    def test_total_processed(self):
        """Test total_processed calculation."""
        result = IngestionResult(created=5, updated=3)
        assert result.total_processed == 8

    def test_to_dict(self):
        """Test to_dict conversion."""
        result = IngestionResult(created=5, updated=3, errors=1, details=["test"])
        d = result.to_dict()

        assert d["created"] == 5
        assert d["updated"] == 3
        assert d["errors"] == 1
        assert d["total_processed"] == 8
        assert d["details"] == ["test"]

```

---

# FILE: `espn_service/tests/test_ingestion_new.py`

```python
"""Tests for new ingestion services and REST API endpoints.

Covers: NewsIngestionService, InjuryIngestionService, TransactionIngestionService,
Celery tasks, and REST GET endpoints for news/injuries/transactions/athlete-stats.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.espn.models import Injury, League, NewsArticle, Sport, Team, Transaction
from apps.ingest.services import (
    InjuryIngestionService,
    IngestionResult,
    NewsIngestionService,
    TransactionIngestionService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_league(sport_slug: str = "basketball", league_slug: str = "nba") -> tuple[Sport, League]:
    sport, _ = Sport.objects.get_or_create(slug=sport_slug, defaults={"name": sport_slug.title()})
    league, _ = League.objects.get_or_create(
        sport=sport,
        slug=league_slug,
        defaults={"name": league_slug.upper(), "abbreviation": league_slug.upper()[:5]},
    )
    return sport, league


def _make_espn_response(data: dict) -> MagicMock:
    resp = MagicMock()
    resp.data = data
    return resp


# ---------------------------------------------------------------------------
# NewsIngestionService
# ---------------------------------------------------------------------------


class TestNewsIngestionService(TestCase):
    """Tests for NewsIngestionService.ingest_news()."""

    def setUp(self) -> None:
        self.client_mock = MagicMock()
        self.service = NewsIngestionService(client=self.client_mock)
        _, self.league = _make_league("basketball", "nba")

    def test_ingest_creates_new_articles(self) -> None:
        """Two new articles should be created."""
        self.client_mock.get_news.return_value = _make_espn_response({
            "articles": [
                {
                    "dataSourceIdentifier": "art-001",
                    "headline": "LeBron scores 50",
                    "published": "2024-01-15T20:00:00Z",
                    "type": "Story",
                },
                {
                    "dataSourceIdentifier": "art-002",
                    "headline": "NBA All-Star rosters announced",
                    "published": "2024-01-16T18:00:00Z",
                    "type": "Story",
                },
            ]
        })

        result = self.service.ingest_news("basketball", "nba")

        assert isinstance(result, IngestionResult)
        assert result.created == 2
        assert result.updated == 0
        assert result.errors == 0
        assert NewsArticle.objects.count() == 2

    def test_ingest_updates_existing_article(self) -> None:
        """Ingesting the same espn_id twice should update, not create."""
        self.client_mock.get_news.return_value = _make_espn_response({
            "articles": [
                {
                    "dataSourceIdentifier": "art-001",
                    "headline": "Updated headline",
                    "published": "2024-01-15T20:00:00Z",
                    "type": "Story",
                }
            ]
        })

        NewsArticle.objects.create(espn_id="art-001", headline="Old headline")

        result = self.service.ingest_news("basketball", "nba")

        assert result.created == 0
        assert result.updated == 1
        assert NewsArticle.objects.get(espn_id="art-001").headline == "Updated headline"

    def test_ingest_empty_response_returns_zero(self) -> None:
        self.client_mock.get_news.return_value = _make_espn_response({"articles": []})
        result = self.service.ingest_news("basketball", "nba")
        assert result.created == 0
        assert result.updated == 0
        assert result.errors == 0

    def test_ingest_skips_items_without_espn_id(self) -> None:
        self.client_mock.get_news.return_value = _make_espn_response({
            "articles": [{"headline": "No ID article"}]
        })
        result = self.service.ingest_news("basketball", "nba")
        assert result.errors == 1
        assert NewsArticle.objects.count() == 0


# ---------------------------------------------------------------------------
# InjuryIngestionService
# ---------------------------------------------------------------------------


class TestInjuryIngestionService(TestCase):
    """Tests for InjuryIngestionService.ingest_injuries()."""

    def setUp(self) -> None:
        self.client_mock = MagicMock()
        self.service = InjuryIngestionService(client=self.client_mock)
        sport, self.league = _make_league("football", "nfl")
        self.team = Team.objects.create(
            league=self.league,
            espn_id="18",
            abbreviation="KC",
            display_name="Kansas City Chiefs",
        )

    def test_ingest_creates_injury_records(self) -> None:
        self.client_mock.get_league_injuries.return_value = _make_espn_response({
            "items": [
                {
                    "athlete": {"id": "3139477", "displayName": "Patrick Mahomes", "position": {"abbreviation": "QB"}},
                    "status": "Questionable",
                    "description": "Ankle",
                    "type": "Ankle",
                    "team": {"id": "18"},
                },
            ]
        })

        result = self.service.ingest_injuries("football", "nfl")

        assert result.created == 1
        assert result.errors == 0
        injury = Injury.objects.get(league=self.league)
        assert injury.athlete_name == "Patrick Mahomes"
        assert injury.status == "questionable"
        assert injury.team == self.team

    def test_ingest_clears_stale_records(self) -> None:
        """Re-ingesting should wipe old records and insert fresh ones."""
        Injury.objects.create(league=self.league, athlete_name="Old Player", status="out")

        self.client_mock.get_league_injuries.return_value = _make_espn_response({
            "items": [
                {
                    "athlete": {"id": "999", "displayName": "New Player"},
                    "status": "Out",
                    "team": {},
                }
            ]
        })

        self.service.ingest_injuries("football", "nfl")

        assert Injury.objects.filter(league=self.league).count() == 1
        assert Injury.objects.filter(league=self.league).first().athlete_name == "New Player"

    def test_ingest_empty_response(self) -> None:
        self.client_mock.get_league_injuries.return_value = _make_espn_response({"items": []})
        result = self.service.ingest_injuries("football", "nfl")
        assert result.created == 0

    def test_status_normalisation(self) -> None:
        service = InjuryIngestionService.__new__(InjuryIngestionService)
        assert service._normalize_status("Out") == "out"
        assert service._normalize_status("QUESTIONABLE") == "questionable"
        assert service._normalize_status("Injured Reserve") == "ir"
        assert service._normalize_status("Day-to-Day") == "day_to_day"
        assert service._normalize_status("Unknown") == "other"


# ---------------------------------------------------------------------------
# TransactionIngestionService
# ---------------------------------------------------------------------------


class TestTransactionIngestionService(TestCase):
    """Tests for TransactionIngestionService.ingest_transactions()."""

    def setUp(self) -> None:
        self.client_mock = MagicMock()
        self.service = TransactionIngestionService(client=self.client_mock)
        _, self.league = _make_league("basketball", "nba")

    def test_ingest_creates_transactions(self) -> None:
        self.client_mock.get_league_transactions.return_value = _make_espn_response({
            "items": [
                {
                    "id": "txn-101",
                    "description": "Lakers signed X to a 1-year deal",
                    "type": "Signing",
                    "date": "2024-07-15",
                    "athlete": {"id": "555", "displayName": "Player X"},
                    "team": {},
                }
            ]
        })

        result = self.service.ingest_transactions("basketball", "nba")

        assert result.created == 1
        txn = Transaction.objects.get(espn_id="txn-101")
        assert txn.type == "Signing"
        assert txn.date == date(2024, 7, 15)

    def test_ingest_updates_existing_transaction(self) -> None:
        Transaction.objects.create(league=self.league, espn_id="txn-101", description="Old")

        self.client_mock.get_league_transactions.return_value = _make_espn_response({
            "items": [
                {
                    "id": "txn-101",
                    "description": "Updated description",
                    "type": "Trade",
                    "date": "2024-07-20",
                    "athlete": {},
                    "team": {},
                }
            ]
        })

        result = self.service.ingest_transactions("basketball", "nba")

        assert result.updated == 1
        assert Transaction.objects.get(espn_id="txn-101").description == "Updated description"


# ---------------------------------------------------------------------------
# Celery tasks
# ---------------------------------------------------------------------------


class TestNewCeleryTasks(TestCase):
    """Verify new Celery task functions dispatch services correctly."""

    @patch("apps.ingest.services.NewsIngestionService")
    def test_refresh_news_task_calls_service(self, MockService: MagicMock) -> None:
        from apps.ingest.tasks import refresh_news_task

        mock_instance = MockService.return_value
        mock_instance.ingest_news.return_value = IngestionResult(created=5, updated=0, errors=0)

        # bind=True tasks must be tested via .run() to skip the self/broker machinery
        result = refresh_news_task.run("basketball", "nba")

        mock_instance.ingest_news.assert_called_once_with("basketball", "nba", limit=50)
        assert result["created"] == 5

    @patch("apps.ingest.services.InjuryIngestionService")
    def test_refresh_injuries_task_calls_service(self, MockService: MagicMock) -> None:
        from apps.ingest.tasks import refresh_injuries_task

        mock_instance = MockService.return_value
        mock_instance.ingest_injuries.return_value = IngestionResult(created=30, updated=0, errors=0)

        result = refresh_injuries_task.run("football", "nfl")

        mock_instance.ingest_injuries.assert_called_once_with("football", "nfl")
        assert result["created"] == 30

    @patch("apps.ingest.services.TransactionIngestionService")
    def test_refresh_transactions_task_calls_service(self, MockService: MagicMock) -> None:
        from apps.ingest.tasks import refresh_transactions_task

        mock_instance = MockService.return_value
        mock_instance.ingest_transactions.return_value = IngestionResult(created=8, updated=2, errors=0)

        result = refresh_transactions_task.run("basketball", "nba")

        mock_instance.ingest_transactions.assert_called_once_with("basketball", "nba")
        assert result["created"] == 8


# ---------------------------------------------------------------------------
# REST API endpoints
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestNewsArticleAPI:
    """Tests for GET /api/v1/news/"""

    def test_list_news_empty(self) -> None:
        client = APIClient()
        response = client.get("/api/v1/news/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0

    def test_list_news_filter_by_league(self) -> None:
        sport, league = _make_league("basketball", "nba")
        sport2, league2 = _make_league("football", "nfl")
        NewsArticle.objects.create(espn_id="a1", headline="NBA news", league=league)
        NewsArticle.objects.create(espn_id="a2", headline="NFL news", league=league2)

        client = APIClient()
        response = client.get("/api/v1/news/?league=nba")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["headline"] == "NBA news"


@pytest.mark.django_db
class TestInjuryAPI:
    """Tests for GET /api/v1/injuries/"""

    def test_list_injuries_empty(self) -> None:
        client = APIClient()
        response = client.get("/api/v1/injuries/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0

    def test_list_injuries_filter_by_status(self) -> None:
        _, league = _make_league("football", "nfl")
        Injury.objects.create(league=league, athlete_name="Player A", status="out")
        Injury.objects.create(league=league, athlete_name="Player B", status="questionable")

        client = APIClient()
        response = client.get("/api/v1/injuries/?status=out")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["athlete_name"] == "Player A"


@pytest.mark.django_db
class TestIngestNewsEndpoint:
    """Tests for POST /api/v1/ingest/news/"""

    def test_invalid_request_returns_400(self) -> None:
        client = APIClient()
        response = client.post("/api/v1/ingest/news/", {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("apps.ingest.views.NewsIngestionService")
    def test_valid_request_calls_service(self, MockService: MagicMock) -> None:
        mock_instance = MockService.return_value
        mock_instance.ingest_news.return_value = IngestionResult(created=3, updated=0, errors=0)

        client = APIClient()
        response = client.post(
            "/api/v1/ingest/news/",
            {"sport": "basketball", "league": "nba"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["created"] == 3
        mock_instance.ingest_news.assert_called_once_with("basketball", "nba", limit=50)


@pytest.mark.django_db
class TestIngestInjuriesEndpoint:
    """Tests for POST /api/v1/ingest/injuries/"""

    def test_invalid_request_returns_400(self) -> None:
        client = APIClient()
        response = client.post("/api/v1/ingest/injuries/", {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("apps.ingest.views.InjuryIngestionService")
    def test_valid_request_calls_service(self, MockService: MagicMock) -> None:
        mock_instance = MockService.return_value
        mock_instance.ingest_injuries.return_value = IngestionResult(created=22, updated=0, errors=0)

        client = APIClient()
        response = client.post(
            "/api/v1/ingest/injuries/",
            {"sport": "football", "league": "nfl"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["created"] == 22

```

---

# FILE: `espn_service/tests/test_models.py`

```python
"""Tests for ESPN models."""

from datetime import UTC, datetime

import pytest

from apps.espn.models import Athlete, Competitor, Event, League, Sport, Team, Venue


@pytest.mark.django_db
class TestSportModel:
    """Tests for Sport model."""

    def test_sport_str(self, sport: Sport):
        """Test Sport string representation."""
        assert str(sport) == "Basketball"

    def test_sport_ordering(self, db):
        """Test Sport ordering by name."""
        Sport.objects.create(slug="football", name="Football")
        Sport.objects.create(slug="baseball", name="Baseball")

        sports = list(Sport.objects.all())
        assert sports[0].name == "Baseball"
        assert sports[1].name == "Football"


@pytest.mark.django_db
class TestLeagueModel:
    """Tests for League model."""

    def test_league_str(self, league: League):
        """Test League string representation."""
        assert str(league) == "NBA (Basketball)"

    def test_league_unique_constraint(self, sport: Sport, league: League):
        """Test League unique constraint on sport+slug."""
        with pytest.raises(Exception):  # IntegrityError
            League.objects.create(
                sport=sport,
                slug="nba",
                name="Duplicate NBA",
            )


@pytest.mark.django_db
class TestTeamModel:
    """Tests for Team model."""

    def test_team_str(self, team: Team):
        """Test Team string representation."""
        assert str(team) == "Test Team (NBA)"

    def test_team_primary_logo(self, team: Team):
        """Test Team primary_logo property."""
        assert team.primary_logo == "https://example.com/logo.png"

    def test_team_primary_logo_no_default(self, league: League):
        """Test Team primary_logo when no default logo."""
        team = Team.objects.create(
            league=league,
            espn_id="99",
            abbreviation="XYZ",
            display_name="No Logo Team",
            logos=[{"href": "https://example.com/alt.png", "rel": ["full"]}],
        )
        assert team.primary_logo == "https://example.com/alt.png"

    def test_team_primary_logo_empty(self, league: League):
        """Test Team primary_logo when no logos."""
        team = Team.objects.create(
            league=league,
            espn_id="99",
            abbreviation="XYZ",
            display_name="No Logo Team",
        )
        assert team.primary_logo is None

    def test_team_unique_constraint(self, team: Team, league: League):
        """Test Team unique constraint on league+espn_id."""
        with pytest.raises(Exception):  # IntegrityError
            Team.objects.create(
                league=league,
                espn_id="1",  # Same as team fixture
                abbreviation="DUP",
                display_name="Duplicate Team",
            )


@pytest.mark.django_db
class TestVenueModel:
    """Tests for Venue model."""

    def test_venue_str_with_location(self, venue: Venue):
        """Test Venue string representation with location."""
        assert str(venue) == "Test Arena (Test City, TS)"

    def test_venue_str_no_location(self, db):
        """Test Venue string representation without location."""
        venue = Venue.objects.create(
            espn_id="5678",
            name="Arena Only",
        )
        assert str(venue) == "Arena Only"


@pytest.mark.django_db
class TestEventModel:
    """Tests for Event model."""

    def test_event_str(self, event: Event):
        """Test Event string representation."""
        assert "TST @ OPP" in str(event)
        assert "2024-12-15" in str(event)

    def test_event_status_choices(self, league: League):
        """Test Event status choices."""
        event = Event.objects.create(
            league=league,
            espn_id="123",
            date=datetime.now(UTC),
            name="Test Event",
            season_year=2024,
            season_type=2,
            status=Event.STATUS_IN_PROGRESS,
        )
        assert event.status == "in_progress"

    def test_event_unique_constraint(self, event: Event, league: League):
        """Test Event unique constraint on league+espn_id."""
        with pytest.raises(Exception):  # IntegrityError
            Event.objects.create(
                league=league,
                espn_id="401584666",  # Same as event fixture
                date=datetime.now(UTC),
                name="Duplicate Event",
                season_year=2024,
                season_type=2,
            )


@pytest.mark.django_db
class TestCompetitorModel:
    """Tests for Competitor model."""

    def test_competitor_str(self, competitor_home: Competitor):
        """Test Competitor string representation."""
        assert "TST" in str(competitor_home)
        assert "home" in str(competitor_home)

    def test_competitor_score_int(self, competitor_home: Competitor):
        """Test Competitor score_int property."""
        assert competitor_home.score_int == 110

    def test_competitor_score_int_empty(self, event: Event, team: Team):
        """Test Competitor score_int when empty."""
        competitor = Competitor.objects.create(
            event=event,
            team=team,
            home_away=Competitor.HOME,
            order=0,
        )
        assert competitor.score_int is None

    def test_competitor_score_int_invalid(self, event: Event, team: Team):
        """Test Competitor score_int when invalid."""
        competitor = Competitor.objects.create(
            event=event,
            team=team,
            home_away=Competitor.HOME,
            score="N/A",
            order=0,
        )
        assert competitor.score_int is None


@pytest.mark.django_db
class TestAthleteModel:
    """Tests for Athlete model."""

    def test_athlete_str_with_team(self, team: Team):
        """Test Athlete string representation with team."""
        athlete = Athlete.objects.create(
            espn_id="12345",
            first_name="Test",
            last_name="Player",
            full_name="Test Player",
            display_name="T. Player",
            team=team,
        )
        assert str(athlete) == "T. Player (TST)"

    def test_athlete_str_free_agent(self, db):
        """Test Athlete string representation as free agent."""
        athlete = Athlete.objects.create(
            espn_id="12345",
            first_name="Test",
            last_name="Player",
            full_name="Test Player",
            display_name="T. Player",
        )
        assert str(athlete) == "T. Player (FA)"

```

---

# FILE: `nhl_service/.env.example`

```
NHL_API_WEB_BASE_URL=https://api-web.nhle.com
NHL_API_STATS_BASE_URL=https://api.nhle.com/stats/rest
NHL_API_TIMEOUT=30
NHL_API_RETRIES=3

# Django
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Database (PostgreSQL)
DATABASE_URL=postgres://nhl_user:nhl_pass@localhost:5432/nhl_db

# Cache / Celery (Redis)
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

```

---

# FILE: `nhl_service/.gitignore`

```
# Django / Python
__pycache__/
*.py[cod]
*.pyo
*.egg
*.egg-info/
dist/
build/
.eggs/
.venv/
venv/
env/

# Environment
.env
.env.local
.env.*.local

# Django
db.sqlite3
media/
staticfiles/

# Coverage / testing
.coverage
htmlcov/
.pytest_cache/
.mypy_cache/
.ruff_cache/
coverage.xml

# Logs
*.log

# OS
.DS_Store
Thumbs.db

```

---

# FILE: `nhl_service/Dockerfile`

```
# Base image
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir build && \
    pip wheel --no-deps --requirement <(python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']))") -w /wheels

# Final stage
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder and install
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# Copy application code
COPY . .

# Run as non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE="config.settings.production"

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--access-logfile", "-", "--error-logfile", "-"]

```

---

# FILE: `nhl_service/Makefile`

```
.PHONY: all help install format lint test migrate run local shell ingest

all: help

help:
	@echo "Available commands:"
	@echo "  install    - Install dependencies (with dev group)"
	@echo "  format     - Auto-format code with ruff"
	@echo "  lint       - Lint and typecheck with ruff/mypy"
	@echo "  test       - Run pytest suite with coverage"
	@echo "  migrate    - Run Django database migrations"
	@echo "  run        - Make migrations and run local dev server"
	@echo "  shell      - Open Django shell_plus"

install:
	pip install -e ".[dev]"

format:
	ruff check --fix .
	ruff format .

lint:
	ruff check .
	mypy .

test:
	pytest tests/

migrate:
	python manage.py makemigrations
	python manage.py migrate

run: migrate
	python manage.py runserver 0.0.0.0:8001

shell:
	python manage.py shell

```

---

# FILE: `nhl_service/apps/__init__.py`

```python
"""Apps namespace."""

```

---

# FILE: `nhl_service/apps/ingest/__init__.py`

```python
"""Ingestion package."""

```

---

# FILE: `nhl_service/apps/ingest/apps.py`

```python
"""Ingest app initialization."""

from django.apps import AppConfig


class IngestConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ingest"
    verbose_name = "NHL Data Ingestion"

```

---

# FILE: `nhl_service/apps/ingest/tasks.py`

```python
"""Celery ingestion tasks for NHL data."""

import logging
from datetime import datetime
from typing import Any

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.nhl.models import (
    Game,
    GoalieSeasonStats,
    Player,
    SkaterSeasonStats,
    Standing,
    Team,
)
from clients.nhl_client import NHLStatsClient, NHLWebClient

logger = logging.getLogger(__name__)


@shared_task
def sync_teams() -> str:
    """Sync all NHL teams from the Stats REST API."""
    stats_client = NHLStatsClient()
    response = stats_client.get_teams()
    teams_data: list[dict[str, Any]] = response.get("data", [])

    created_count = 0
    updated_count = 0

    with transaction.atomic():
        # Set all to inactive first, then mark active if they appear in the feed
        Team.objects.update(is_active=False)

        for t_data in teams_data:
            # Stats API team IDs are ints in the feed
            team_id = str(t_data.get("id"))
            if not team_id:
                continue

            # Some fields
            name = t_data.get("fullName", "")
            abbrev = t_data.get("triCode", "")
            if not abbrev:
                abbrev = t_data.get("rawTricode", "")
                
            franchise_id = str(t_data.get("franchiseId", ""))

            team, created = Team.objects.update_or_create(
                team_id=team_id,
                defaults={
                    "abbreviation": abbrev,
                    "name": name.split()[-1] if name else "",
                    "full_name": name,
                    "franchise_id": franchise_id,
                    "is_active": True,
                    "raw_data": t_data,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

    return f"Teams sync complete. Created: {created_count}, Updated: {updated_count}"


@shared_task
def sync_team_rosters() -> str:
    """Sync current active players from all active teams."""
    web_client = NHLWebClient()
    active_teams = Team.objects.filter(is_active=True)
    
    total_created = 0
    total_updated = 0

    # We do not mark all inactive here, as we loop team by team.
    # A full player sync would need to handle trades and demotions strictly.
    # This is a simplified active roster ingestion.

    for team in active_teams:
        try:
            roster_data = web_client.get_roster(team.abbreviation)
            
            # Roster has 'forwards', 'defensemen', 'goalies'
            players_in_roster = []
            players_in_roster.extend(roster_data.get("forwards", []))
            players_in_roster.extend(roster_data.get("defensemen", []))
            players_in_roster.extend(roster_data.get("goalies", []))

            with transaction.atomic():
                # For basic sync, just ensure they exist
                for p_data in players_in_roster:
                    player_id = str(p_data.get("id"))
                    first_name = p_data.get("firstName", {}).get("default", "")
                    last_name = p_data.get("lastName", {}).get("default", "")
                    full_name = f"{first_name} {last_name}".strip()
                    
                    sweater = str(p_data.get("sweaterNumber", ""))
                    position = p_data.get("positionCode", "")
                    headshot = p_data.get("headshot", "")

                    player, created = Player.objects.update_or_create(
                        player_id=player_id,
                        defaults={
                            "first_name": first_name,
                            "last_name": last_name,
                            "full_name": full_name,
                            "sweater_number": sweater,
                            "position": position,
                            "current_team": team,
                            "is_active": True,
                            "headshot_url": headshot,
                            "raw_data": p_data,
                        },
                    )
                    
                    if created:
                        total_created += 1
                    else:
                        total_updated += 1
                        
        except Exception as e:
            logger.error("Failed to sync roster for %s: %s", team.abbreviation, e)

    return f"Roster sync complete. Created: {total_created}, Updated: {total_updated}"


@shared_task
def sync_standings() -> str:
    """Sync current league standings."""
    web_client = NHLWebClient()
    response = web_client.get_standings()
    
    standings_data = response.get("standings", [])
    if not standings_data:
        return "No standings data found."
        
    date_str = response.get("standingsDate", timezone.now().strftime("%Y-%m-%d"))
    # The API might give the 'now' datetime, slice to YYYY-MM-DD
    sync_date = datetime.strptime(date_str[:10], "%Y-%m-%d").date()

    created_count = 0
    updated_count = 0

    with transaction.atomic():
        for st_data in standings_data:
            team_abbrev = st_data.get("teamAbbrev", {}).get("default", "")
            if not team_abbrev:
                # Sometimes it's a flat string in different responses, check both
                team_abbrev = st_data.get("teamAbbrev", "")
                if isinstance(team_abbrev, dict):
                    team_abbrev = team_abbrev.get("default", "")

            # If team missing, try finding by name or just skip
            try:
                team = Team.objects.get(abbreviation=team_abbrev)
            except Team.DoesNotExist:
                logger.warning("Team %s not found in DB. Run sync_teams first.", team_abbrev)
                continue

            games_played = st_data.get("gamesPlayed", 0)
            wins = st_data.get("wins", 0)
            losses = st_data.get("losses", 0)
            ot_losses = st_data.get("otLosses", 0)
            points = st_data.get("points", 0)
            point_pct = st_data.get("pointPctg", 0.0)
            
            div_name = st_data.get("divisionName", "")
            conf_name = st_data.get("conferenceName", "")

            standing, created = Standing.objects.update_or_create(
                team=team,
                date=sync_date,
                defaults={
                    "games_played": games_played,
                    "wins": wins,
                    "losses": losses,
                    "ot_losses": ot_losses,
                    "points": points,
                    "point_pct": point_pct,
                    "division_name": div_name,
                    "conference_name": conf_name,
                    "raw_data": st_data,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

    return f"Standings sync complete for {sync_date}. Created: {created_count}, Updated: {updated_count}"

```

---

# FILE: `nhl_service/apps/nhl/admin.py`

```python
"""Django admin configuration for NHL models."""

from django.contrib import admin

from apps.nhl.models import (
    Game,
    GoalieSeasonStats,
    Player,
    SkaterSeasonStats,
    Standing,
    Team,
)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("full_name", "abbreviation", "team_id", "is_active")
    search_fields = ("full_name", "abbreviation")


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("full_name", "sweater_number", "position", "current_team", "is_active")
    search_fields = ("full_name", "last_name", "player_id")
    list_filter = ("position", "is_active", "current_team")


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("date", "away_team", "home_team", "status", "season")
    list_filter = ("status", "season", "game_type")
    search_fields = ("game_id",)


@admin.register(Standing)
class StandingAdmin(admin.ModelAdmin):
    list_display = ("team", "date", "points", "games_played")
    list_filter = ("date", "team")


@admin.register(SkaterSeasonStats)
class SkaterSeasonStatsAdmin(admin.ModelAdmin):
    list_display = ("player", "season", "points", "goals", "assists")
    list_filter = ("season",)
    search_fields = ("player__full_name",)


@admin.register(GoalieSeasonStats)
class GoalieSeasonStatsAdmin(admin.ModelAdmin):
    list_display = ("player", "season", "wins", "save_pct", "gaa")
    list_filter = ("season",)
    search_fields = ("player__full_name",)

```

---

# FILE: `nhl_service/apps/nhl/apps.py`

```python
"""NHL app initialization."""

from django.apps import AppConfig


class NhlConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.nhl"
    verbose_name = "National Hockey League"

```

---

# FILE: `nhl_service/apps/nhl/migrations/0001_initial.py`

```python
# Generated by Django 5.2.12 on 2026-03-26 20:23

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Team",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "team_id",
                    models.CharField(db_index=True, max_length=50, unique=True),
                ),
                ("abbreviation", models.CharField(max_length=10)),
                ("name", models.CharField(max_length=100)),
                ("full_name", models.CharField(max_length=100)),
                ("franchise_id", models.CharField(blank=True, max_length=50)),
                ("is_active", models.BooleanField(default=True)),
                ("raw_data", models.JSONField(blank=True, default=dict)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Player",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "player_id",
                    models.CharField(db_index=True, max_length=50, unique=True),
                ),
                ("first_name", models.CharField(max_length=50)),
                ("last_name", models.CharField(max_length=50)),
                ("full_name", models.CharField(max_length=100)),
                ("sweater_number", models.CharField(blank=True, max_length=10)),
                ("position", models.CharField(blank=True, max_length=10)),
                ("is_active", models.BooleanField(default=True)),
                ("headshot_url", models.URLField(blank=True, max_length=500)),
                ("raw_data", models.JSONField(blank=True, default=dict)),
                (
                    "current_team",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="players",
                        to="nhl.team",
                    ),
                ),
            ],
            options={
                "ordering": ["last_name", "first_name"],
            },
        ),
        migrations.CreateModel(
            name="Game",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "game_id",
                    models.CharField(db_index=True, max_length=50, unique=True),
                ),
                ("season", models.CharField(db_index=True, max_length=20)),
                ("game_type", models.PositiveSmallIntegerField(default=2)),
                ("date", models.DateTimeField(db_index=True)),
                ("home_score", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("away_score", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("status", models.CharField(default="scheduled", max_length=50)),
                ("raw_data", models.JSONField(blank=True, default=dict)),
                (
                    "away_team",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="away_games",
                        to="nhl.team",
                    ),
                ),
                (
                    "home_team",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="home_games",
                        to="nhl.team",
                    ),
                ),
            ],
            options={
                "ordering": ["-date"],
            },
        ),
        migrations.CreateModel(
            name="GoalieSeasonStats",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("season", models.CharField(db_index=True, max_length=20)),
                ("games_played", models.PositiveSmallIntegerField(default=0)),
                ("wins", models.PositiveSmallIntegerField(default=0)),
                ("losses", models.PositiveSmallIntegerField(default=0)),
                ("save_pct", models.FloatField(blank=True, null=True)),
                ("gaa", models.FloatField(blank=True, null=True)),
                ("shutouts", models.PositiveSmallIntegerField(default=0)),
                ("raw_data", models.JSONField(blank=True, default=dict)),
                (
                    "player",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="goalie_stats",
                        to="nhl.player",
                    ),
                ),
            ],
            options={
                "ordering": ["-season", "-wins"],
                "unique_together": {("player", "season")},
            },
        ),
        migrations.CreateModel(
            name="SkaterSeasonStats",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("season", models.CharField(db_index=True, max_length=20)),
                ("games_played", models.PositiveSmallIntegerField(default=0)),
                ("goals", models.PositiveSmallIntegerField(default=0)),
                ("assists", models.PositiveSmallIntegerField(default=0)),
                ("points", models.PositiveSmallIntegerField(default=0)),
                ("plus_minus", models.SmallIntegerField(default=0)),
                ("raw_data", models.JSONField(blank=True, default=dict)),
                (
                    "player",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="skater_stats",
                        to="nhl.player",
                    ),
                ),
            ],
            options={
                "ordering": ["-season", "-points"],
                "unique_together": {("player", "season")},
            },
        ),
        migrations.CreateModel(
            name="Standing",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("date", models.DateField(db_index=True)),
                ("games_played", models.PositiveSmallIntegerField(default=0)),
                ("wins", models.PositiveSmallIntegerField(default=0)),
                ("losses", models.PositiveSmallIntegerField(default=0)),
                ("ot_losses", models.PositiveSmallIntegerField(default=0)),
                ("points", models.PositiveSmallIntegerField(default=0)),
                ("point_pct", models.FloatField(blank=True, null=True)),
                ("division_name", models.CharField(blank=True, max_length=100)),
                ("conference_name", models.CharField(blank=True, max_length=100)),
                ("raw_data", models.JSONField(blank=True, default=dict)),
                (
                    "team",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="standings",
                        to="nhl.team",
                    ),
                ),
            ],
            options={
                "ordering": ["-date", "-points"],
                "unique_together": {("team", "date")},
            },
        ),
    ]

```

---

# FILE: `nhl_service/apps/nhl/migrations/__init__.py`

```python

```

---

# FILE: `nhl_service/apps/nhl/models.py`

```python
"""Database models for NHL functionality."""

from django.db import models


class TimestampMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Team(TimestampMixin):
    """NHL Team."""
    team_id = models.CharField(max_length=50, unique=True, db_index=True)
    abbreviation = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    full_name = models.CharField(max_length=100)
    franchise_id = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.abbreviation})"


class Player(TimestampMixin):
    """NHL Player / Skater / Goalie."""
    player_id = models.CharField(max_length=50, unique=True, db_index=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    full_name = models.CharField(max_length=100)
    sweater_number = models.CharField(max_length=10, blank=True)
    position = models.CharField(max_length=10, blank=True)
    current_team = models.ForeignKey(
        Team, on_delete=models.SET_NULL, null=True, blank=True, related_name="players"
    )
    is_active = models.BooleanField(default=True)
    headshot_url = models.URLField(max_length=500, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.full_name} #{self.sweater_number}"


class Game(TimestampMixin):
    """NHL Game / Event."""
    game_id = models.CharField(max_length=50, unique=True, db_index=True)
    season = models.CharField(max_length=20, db_index=True)  # e.g. "20232024"
    game_type = models.PositiveSmallIntegerField(default=2)  # 1=Pre, 2=Reg, 3=Playoff
    date = models.DateTimeField(db_index=True)
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="home_games")
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="away_games")
    home_score = models.PositiveSmallIntegerField(null=True, blank=True)
    away_score = models.PositiveSmallIntegerField(null=True, blank=True)
    status = models.CharField(max_length=50, default="scheduled")
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self) -> str:
        return f"{self.away_team.abbreviation} @ {self.home_team.abbreviation} ({self.date.date()})"


class Standing(TimestampMixin):
    """Team Season Standing."""
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="standings")
    date = models.DateField(db_index=True)
    games_played = models.PositiveSmallIntegerField(default=0)
    wins = models.PositiveSmallIntegerField(default=0)
    losses = models.PositiveSmallIntegerField(default=0)
    ot_losses = models.PositiveSmallIntegerField(default=0)
    points = models.PositiveSmallIntegerField(default=0)
    point_pct = models.FloatField(null=True, blank=True)
    division_name = models.CharField(max_length=100, blank=True)
    conference_name = models.CharField(max_length=100, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-date", "-points"]
        unique_together = [["team", "date"]]

    def __str__(self) -> str:
        return f"{self.team.abbreviation} - {self.points} pts ({self.date})"


class SkaterSeasonStats(TimestampMixin):
    """Skater season stats (from Stats REST API)."""
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="skater_stats")
    season = models.CharField(max_length=20, db_index=True)
    games_played = models.PositiveSmallIntegerField(default=0)
    goals = models.PositiveSmallIntegerField(default=0)
    assists = models.PositiveSmallIntegerField(default=0)
    points = models.PositiveSmallIntegerField(default=0)
    plus_minus = models.SmallIntegerField(default=0)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-season", "-points"]
        unique_together = [["player", "season"]]

    def __str__(self) -> str:
        return f"{self.player.full_name} ({self.season}): {self.points} pts"


class GoalieSeasonStats(TimestampMixin):
    """Goalie season stats (from Stats REST API)."""
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="goalie_stats")
    season = models.CharField(max_length=20, db_index=True)
    games_played = models.PositiveSmallIntegerField(default=0)
    wins = models.PositiveSmallIntegerField(default=0)
    losses = models.PositiveSmallIntegerField(default=0)
    save_pct = models.FloatField(null=True, blank=True)
    gaa = models.FloatField(null=True, blank=True)
    shutouts = models.PositiveSmallIntegerField(default=0)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-season", "-wins"]
        unique_together = [["player", "season"]]

    def __str__(self) -> str:
        return f"{self.player.full_name} ({self.season}): {self.wins} W"

```

---

# FILE: `nhl_service/apps/nhl/serializers.py`

```python
"""DRF Serializers for NHL models."""

from rest_framework import serializers

from apps.nhl.models import (
    Game,
    GoalieSeasonStats,
    Player,
    SkaterSeasonStats,
    Standing,
    Team,
)


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["id", "team_id", "abbreviation", "name", "full_name", "franchise_id", "is_active", "raw_data"]


class PlayerSerializer(serializers.ModelSerializer):
    current_team = TeamSerializer(read_only=True)

    class Meta:
        model = Player
        fields = [
            "id", "player_id", "first_name", "last_name", "full_name",
            "sweater_number", "position", "current_team", "is_active", "headshot_url"
        ]


class GameSerializer(serializers.ModelSerializer):
    home_team = TeamSerializer(read_only=True)
    away_team = TeamSerializer(read_only=True)

    class Meta:
        model = Game
        fields = [
            "id", "game_id", "season", "game_type", "date",
            "home_team", "away_team", "home_score", "away_score", "status"
        ]


class StandingSerializer(serializers.ModelSerializer):
    team = TeamSerializer(read_only=True)

    class Meta:
        model = Standing
        fields = [
            "id", "team", "date", "games_played", "wins", "losses", "ot_losses",
            "points", "point_pct", "division_name", "conference_name"
        ]


class SkaterSeasonStatsSerializer(serializers.ModelSerializer):
    player = PlayerSerializer(read_only=True)

    class Meta:
        model = SkaterSeasonStats
        fields = [
            "id", "player", "season", "games_played", "goals", "assists",
            "points", "plus_minus", "raw_data"
        ]


class GoalieSeasonStatsSerializer(serializers.ModelSerializer):
    player = PlayerSerializer(read_only=True)

    class Meta:
        model = GoalieSeasonStats
        fields = [
            "id", "player", "season", "games_played", "wins", "losses",
            "save_pct", "gaa", "shutouts", "raw_data"
        ]

```

---

# FILE: `nhl_service/apps/nhl/views.py`

```python
"""DRF Views for NHL models."""

from rest_framework import viewsets

from apps.nhl.models import (
    Game,
    GoalieSeasonStats,
    Player,
    SkaterSeasonStats,
    Standing,
    Team,
)
from apps.nhl.serializers import (
    GameSerializer,
    GoalieSeasonStatsSerializer,
    PlayerSerializer,
    SkaterSeasonStatsSerializer,
    StandingSerializer,
    TeamSerializer,
)


class TeamViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for NHL Teams."""
    queryset = Team.objects.filter(is_active=True)
    serializer_class = TeamSerializer
    search_fields = ["name", "full_name", "abbreviation"]
    ordering_fields = ["name", "abbreviation"]


class PlayerViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for NHL Players."""
    queryset = Player.objects.select_related("current_team").filter(is_active=True)
    serializer_class = PlayerSerializer
    search_fields = ["first_name", "last_name", "full_name"]
    ordering_fields = ["last_name", "first_name", "sweater_number"]


class GameViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for NHL Games."""
    queryset = Game.objects.select_related("home_team", "away_team")
    serializer_class = GameSerializer
    filterset_fields = ["season", "game_type", "status"]
    ordering_fields = ["date"]


class StandingViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for NHL Standings."""
    queryset = Standing.objects.select_related("team")
    serializer_class = StandingSerializer
    filterset_fields = ["date"]
    ordering_fields = ["points", "date", "point_pct"]


class SkaterSeasonStatsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Skater Season Stats."""
    queryset = SkaterSeasonStats.objects.select_related("player")
    serializer_class = SkaterSeasonStatsSerializer
    filterset_fields = ["season"]
    ordering_fields = ["points", "goals", "assists", "plus_minus"]


class GoalieSeasonStatsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Goalie Season Stats."""
    queryset = GoalieSeasonStats.objects.select_related("player")
    serializer_class = GoalieSeasonStatsSerializer
    filterset_fields = ["season"]
    ordering_fields = ["wins", "save_pct", "gaa", "shutouts"]

```

---

# FILE: `nhl_service/clients/nhl_client.py`

```python
"""HTTP clients for communicating with external NHL APIs."""

import logging
from typing import Any

import httpx
from django.conf import settings
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class NHLWebClient:
    """Client for modern api-web.nhle.com endpoints."""

    def __init__(self) -> None:
        self.base_url = settings.NHL_API_WEB_BASE_URL
        self.client = httpx.Client(timeout=settings.NHL_API_TIMEOUT)

    @retry(stop=stop_after_attempt(settings.NHL_API_RETRIES), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        logger.debug("NHLWebClient GET %s", url)
        response = self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_standings(self) -> dict[str, Any]:
        """Get current standings."""
        return self._get("v1/standings/now")

    def get_roster(self, team_abbrev: str) -> dict[str, Any]:
        """Get current roster for a team."""
        return self._get(f"v1/roster/{team_abbrev}/current")

    def get_player_landing(self, player_id: int | str) -> dict[str, Any]:
        """Get full player profile."""
        return self._get(f"v1/player/{player_id}/landing")

    def get_schedule(self, date: str | None = None) -> dict[str, Any]:
        """Get schedule (now or specific YYYY-MM-DD date)."""
        endpoint = f"v1/schedule/{date}" if date else "v1/schedule/now"
        return self._get(endpoint)

    def get_boxscore(self, game_id: int | str) -> dict[str, Any]:
        """Get game boxscore."""
        return self._get(f"v1/gamecenter/{game_id}/boxscore")


class NHLStatsClient:
    """Client for api.nhle.com/stats/rest endpoints."""

    def __init__(self) -> None:
        self.base_url = settings.NHL_API_STATS_BASE_URL
        self.client = httpx.Client(timeout=settings.NHL_API_TIMEOUT)

    @retry(stop=stop_after_attempt(settings.NHL_API_RETRIES), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        logger.debug("NHLStatsClient GET %s", url)
        response = self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_teams(self) -> dict[str, Any]:
        """Get all teams."""
        return self._get("en/team")

    def get_skater_summary(self, season_id: str, limit: int = -1) -> dict[str, Any]:
        """Get skater scoring summary for a season."""
        params = {"cayenneExp": f"seasonId={season_id}", "limit": limit}
        return self._get("en/skater/summary", params=params)

    def get_goalie_summary(self, season_id: str, limit: int = -1) -> dict[str, Any]:
        """Get goalie summary for a season."""
        params = {"cayenneExp": f"seasonId={season_id}", "limit": limit}
        return self._get("en/goalie/summary", params=params)

```

---

# FILE: `nhl_service/config/__init__.py`

```python
"""Django configuration package for nhl_service."""

```

---

# FILE: `nhl_service/config/asgi.py`

```python
"""ASGI config for nhl_service."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

application = get_asgi_application()

```

---

# FILE: `nhl_service/config/celery.py`

```python
"""Celery application for nhl_service."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("nhl_service")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

```

---

# FILE: `nhl_service/config/settings/__init__.py`

```python
"""Settings package for nhl_service."""

```

---

# FILE: `nhl_service/config/settings/base.py`

```python
"""Base Django settings for nhl_service."""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key-change-in-production")

DEBUG = env("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    # Local
    "apps.nhl",
    "apps.ingest",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database
DATABASES = {
    "default": env.db("DATABASE_URL", default="sqlite:///db.sqlite3"),
}

# Cache & Celery
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# CORS
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:3000"],
)

# drf-spectacular
SPECTACULAR_SETTINGS = {
    "TITLE": "NHL Service API",
    "DESCRIPTION": "Production-ready REST API for NHL sports data — backed by api-web.nhle.com and api.nhle.com/stats/rest.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "CONTACT": {"name": "Joseph Wilson", "email": "jwilson@kloverdevs.ca"},
    "LICENSE": {"name": "MIT"},
}

# NHL API client settings
NHL_API_WEB_BASE_URL = env("NHL_API_WEB_BASE_URL", default="https://api-web.nhle.com")
NHL_API_STATS_BASE_URL = env(
    "NHL_API_STATS_BASE_URL", default="https://api.nhle.com/stats/rest"
)
NHL_API_TIMEOUT = env.int("NHL_API_TIMEOUT", default=30)
NHL_API_RETRIES = env.int("NHL_API_RETRIES", default=3)

```

---

# FILE: `nhl_service/config/settings/local.py`

```python
# ruff: noqa: F401, F403
"""Local development settings."""

from .base import *

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Disable Redis for local dev — use in-memory cache
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Celery — run tasks eagerly in local dev
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

```

---

# FILE: `nhl_service/config/settings/production.py`

```python
# ruff: noqa: F401, F403
"""Production settings."""

from .base import *

DEBUG = False

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

```

---

# FILE: `nhl_service/config/settings/test.py`

```python
# ruff: noqa: F401, F403
"""Test settings — isolated SQLite, no external services."""

from .base import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Speed up password hashing in tests
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

NHL_API_WEB_BASE_URL = "https://api-web.nhle.com"
NHL_API_STATS_BASE_URL = "https://api.nhle.com/stats/rest"

```

---

# FILE: `nhl_service/config/urls.py`

```python
"""URL configuration for nhl_service."""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from apps.nhl import views as nhl_views

router = DefaultRouter()
router.register(r"teams", nhl_views.TeamViewSet, basename="team")
router.register(r"players", nhl_views.PlayerViewSet, basename="player")
router.register(r"games", nhl_views.GameViewSet, basename="game")
router.register(r"standings", nhl_views.StandingViewSet, basename="standing")
router.register(r"skater-stats", nhl_views.SkaterSeasonStatsViewSet, basename="skater-stats")
router.register(r"goalie-stats", nhl_views.GoalieSeasonStatsViewSet, basename="goalie-stats")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(router.urls)),
    # OpenAPI schema + UI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

```

---

# FILE: `nhl_service/config/wsgi.py`

```python
"""WSGI config for nhl_service."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

application = get_wsgi_application()

```

---

# FILE: `nhl_service/docker-compose.yml`

```yaml
version: '3.8'

services:
  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8001
    volumes:
      - .:/app
    ports:
      - "8001:8001"
    env_file:
      - .env
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.local
      - DATABASE_URL=postgres://nhl_user:nhl_pass@db:5432/nhl_db
      - REDIS_URL=redis://redis:6379/1
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  celery:
    build: .
    command: celery -A config worker -l INFO
    volumes:
      - .:/app
    env_file:
      - .env
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.local
      - DATABASE_URL=postgres://nhl_user:nhl_pass@db:5432/nhl_db
      - REDIS_URL=redis://redis:6379/1
    depends_on:
      - db
      - redis

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=nhl_db
      - POSTGRES_USER=nhl_user
      - POSTGRES_PASSWORD=nhl_pass
    volumes:
      - postgres_nhl_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nhl_user -d nhl_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_nhl_data:

```

---

# FILE: `nhl_service/manage.py`

```python
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys


def main() -> None:
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

```

---

# FILE: `nhl_service/pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "nhl-service"
version = "1.0.0"
description = "Production-ready Django REST API for NHL sports data"
readme = "README.md"
requires-python = ">=3.12"
license = {text = "MIT"}
authors = [
    {name = "Joseph Wilson", email = "jwilson@kloverdevs.ca"}
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Framework :: Django :: 5.0",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    "django>=5.0,<6.0",
    "djangorestframework>=3.14,<4.0",
    "django-environ>=0.11,<1.0",
    "django-cors-headers>=4.3,<5.0",
    "django-filter>=24.0,<25.0",
    "drf-spectacular>=0.27,<1.0",
    "psycopg[binary]>=3.1,<4.0",
    "redis>=5.0,<6.0",
    "django-redis>=5.4,<6.0",
    "celery[redis]>=5.3,<6.0",
    "httpx>=0.27,<1.0",
    "tenacity>=8.2,<9.0",
    "structlog>=24.0,<25.0",
    "gunicorn>=21.0,<23.0",
    "whitenoise>=6.6,<7.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0,<9.0",
    "pytest-django>=4.8,<5.0",
    "pytest-cov>=4.1,<6.0",
    "pytest-asyncio>=0.23,<1.0",
    "pytest-httpx>=0.30,<1.0",
    "factory-boy>=3.3,<4.0",
    "faker>=24.0,<25.0",
    "ruff>=0.3,<1.0",
    "mypy>=1.9,<2.0",
    "django-stubs>=4.2,<6.0",
    "djangorestframework-stubs>=3.14,<4.0",
    "pre-commit>=3.6,<4.0",
    "ipython>=8.22,<9.0",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["config*", "apps*", "clients*"]

[tool.ruff]
target-version = "py312"
line-length = 100
exclude = [
    ".git",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "__pycache__",
    "migrations",
]

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # Pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
    "ARG",    # flake8-unused-arguments
    "SIM",    # flake8-simplify
]
ignore = [
    "E501",   # line too long (handled by formatter)
    "B008",   # do not perform function calls in argument defaults
    "ARG001", # unused function argument
]

[tool.ruff.lint.per-file-ignores]
"tests/*" = [
    "ARG002",  # pytest fixtures must match by name even if unused
    "B017",    # blind Exception catch acceptable in test integrity checks
]
"apps/ingest/management/commands/*" = [
    "ARG002",  # Django management command handle() signature is fixed
]

[tool.ruff.lint.isort]
known-first-party = ["config", "apps", "clients"]

[tool.mypy]
python_version = "3.12"
plugins = [
    "mypy_django_plugin.main",
    "mypy_drf_plugin.main",
]
strict = true
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = "*.migrations.*"
ignore_errors = true

[tool.django-stubs]
django_settings_module = "config.settings.local"

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.test"
python_files = ["test_*.py", "*_test.py"]
addopts = [
    "--strict-markers",
    "-ra",
    "-q",
    "--cov=apps",
    "--cov=clients",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-fail-under=80",
]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
]

[tool.coverage.run]
branch = true
source = ["apps", "clients"]
omit = [
    "*/migrations/*",
    "*/tests/*",
    "*/__pycache__/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
]

```

---

# FILE: `nhl_service/tests/__init__.py`

```python
"""Tests package for nhl_service."""

```

---

# FILE: `nhl_service/tests/conftest.py`

```python
"""Pytest configuration and fixtures."""

import pytest
from django.test import Client
from rest_framework.test import APIClient


@pytest.fixture
def client() -> Client:
    """Standard Django client."""
    return Client()


@pytest.fixture
def api_client() -> APIClient:
    """DRF API client."""
    return APIClient()

```

---

# FILE: `nhl_service/tests/test_models.py`

```python
"""Tests for NHL models."""

import pytest
from apps.nhl.models import Team

pytestmark = pytest.mark.django_db


class TestTeamModel:
    def test_team_creation(self) -> None:
        """Test creating a Team model instance."""
        team = Team.objects.create(
            team_id="10",
            abbreviation="TOR",
            name="Maple Leafs",
            full_name="Toronto Maple Leafs",
            franchise_id="5"
        )
        assert team.team_id == "10"
        assert str(team) == "Toronto Maple Leafs (TOR)"
        assert team.is_active is True

```

