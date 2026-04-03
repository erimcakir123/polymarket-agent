# ESPN Public API — Full Reference Index

> Compact index for `espn-public-api-full-reference.md` (18,617 lines).
> Use `Read(offset=START, limit=SIZE)` to load any section on demand.

## How to Use
1. Find the file/section you need in the tables below
2. Read from the full reference: `Read("espn-public-api-full-reference.md", offset=START, limit=SIZE)`
3. No data is lost — all endpoints, code, configs, and docs are preserved in the full file

---

## Root / Project Config (L147–L1646)

| # | File | Lines | Size |
|---|------|-------|------|
| 1 | `.env.example` | 147–189 | 43 |
| 2 | `.gitignore` | 399–585 | 187 |
| 3 | `CHANGELOG.md` | 586–664 | 79 |
| 4 | `CONTRIBUTING.md` | 665–794 | 130 |
| 5 | `README.md` | 795–1563 | 769 |
| 6 | `docker-compose.yml` | 1564–1646 | 83 |

## GitHub CI & Templates (L190–L398)

| # | File | Lines | Size |
|---|------|-------|------|
| 7 | `.github/FUNDING.yml` | 190–198 | 9 |
| 8 | `.github/ISSUE_TEMPLATE/bug_report.md` | 199–243 | 45 |
| 9 | `.github/ISSUE_TEMPLATE/docs_improvement.md` | 244–276 | 33 |
| 10 | `.github/ISSUE_TEMPLATE/missing_endpoint.md` | 277–315 | 39 |
| 11 | `.github/workflows/ci.yml` | 316–398 | 83 |

## Docs Overview (L1647–L1732)

| # | File | Lines | Size |
|---|------|-------|------|
| 12 | `docs/README.md` | 1647–1732 | 86 |

## Response Schemas (L1733–L2597)

| # | File | Lines | Size |
|---|------|-------|------|
| 13 | `docs/response_schemas.md` | 1733–2597 | 865 |

## Sport-Specific API Docs (L2598–L6648)

| # | File | Lines | Size |
|---|------|-------|------|
| 14 | `docs/sports/_global.md` | 2598–3140 | 543 |
| 15 | `docs/sports/australian_football.md` | 3141–3300 | 160 |
| 16 | `docs/sports/baseball.md` | 3301–3519 | 219 |
| 17 | `docs/sports/basketball.md` | 3520–3792 | 273 |
| 18 | `docs/sports/college_sports.md` | 3793–3957 | 165 |
| 19 | `docs/sports/cricket.md` | 3958–4108 | 151 |
| 20 | `docs/sports/field_hockey.md` | 4109–4252 | 144 |
| 21 | `docs/sports/football.md` | 4253–4530 | 278 |
| 22 | `docs/sports/golf.md` | 4531–4695 | 165 |
| 23 | `docs/sports/hockey.md` | 4696–4905 | 210 |
| 24 | `docs/sports/lacrosse.md` | 4906–5055 | 150 |
| 25 | `docs/sports/mma.md` | 5056–5230 | 175 |
| 26 | `docs/sports/racing.md` | 5231–5382 | 152 |
| 27 | `docs/sports/rugby.md` | 5383–5539 | 157 |
| 28 | `docs/sports/rugby_league.md` | 5540–5699 | 160 |
| 29 | `docs/sports/soccer.md` | 5700–6200 | 501 |
| 30 | `docs/sports/tennis.md` | 6201–6358 | 158 |
| 31 | `docs/sports/volleyball.md` | 6359–6503 | 145 |
| 32 | `docs/sports/water_polo.md` | 6504–6648 | 145 |

## ESPN Service — Documentation (L7088–L7461)

| # | File | Lines | Size |
|---|------|-------|------|
| 33 | `espn_service/README.md` | 7088–7461 | 374 |

## ESPN Service — API Client (L11456–L13097)

| # | File | Lines | Size |
|---|------|-------|------|
| 34 | `espn_service/clients/__init__.py` | 11456–11468 | 13 |
| 35 | `espn_service/clients/espn_client.py` | 11469–13097 | 1629 |

## ESPN Service — Models, Views & Serializers (L7781–L9596)

| # | File | Lines | Size |
|---|------|-------|------|
| 36 | `espn_service/apps/espn/__init__.py` | 7781–7789 | 9 |
| 37 | `espn_service/apps/espn/admin.py` | 7790–8015 | 226 |
| 38 | `espn_service/apps/espn/apps.py` | 8016–8034 | 19 |
| 39 | `espn_service/apps/espn/filters.py` | 8035–8159 | 125 |
| 40 | `espn_service/apps/espn/migrations/0001_initial.py` | 8160–8351 | 192 |
| 41 | `espn_service/apps/espn/migrations/0002_injury_newsarticle_transaction_athleteseasonstats.py` | 8352–8468 | 117 |
| 42 | `espn_service/apps/espn/migrations/__init__.py` | 8469–8476 | 8 |
| 43 | `espn_service/apps/espn/models.py` | 8477–8931 | 455 |
| 44 | `espn_service/apps/espn/serializers.py` | 8932–9182 | 251 |
| 45 | `espn_service/apps/espn/urls.py` | 9183–9221 | 39 |
| 46 | `espn_service/apps/espn/views.py` | 9222–9596 | 375 |

## ESPN Service — Data Ingestion (L9597–L11455)

| # | File | Lines | Size |
|---|------|-------|------|
| 47 | `espn_service/apps/ingest/__init__.py` | 9597–9605 | 9 |
| 48 | `espn_service/apps/ingest/apps.py` | 9606–9624 | 19 |
| 49 | `espn_service/apps/ingest/management/__init__.py` | 9625–9633 | 9 |
| 50 | `espn_service/apps/ingest/management/commands/__init__.py` | 9634–9642 | 9 |
| 51 | `espn_service/apps/ingest/management/commands/ingest_all_teams.py` | 9643–9820 | 178 |
| 52 | `espn_service/apps/ingest/management/commands/ingest_injuries.py` | 9821–9876 | 56 |
| 53 | `espn_service/apps/ingest/management/commands/ingest_news.py` | 9877–9945 | 69 |
| 54 | `espn_service/apps/ingest/management/commands/ingest_scoreboard.py` | 9946–10011 | 66 |
| 55 | `espn_service/apps/ingest/management/commands/ingest_teams.py` | 10012–10065 | 54 |
| 56 | `espn_service/apps/ingest/management/commands/ingest_transactions.py` | 10066–10124 | 59 |
| 57 | `espn_service/apps/ingest/serializers.py` | 10125–10232 | 108 |
| 58 | `espn_service/apps/ingest/services.py` | 10233–10952 | 720 |
| 59 | `espn_service/apps/ingest/tasks.py` | 10953–11230 | 278 |
| 60 | `espn_service/apps/ingest/urls.py` | 11231–11259 | 29 |
| 61 | `espn_service/apps/ingest/views.py` | 11260–11455 | 196 |

## ESPN Service — Core Utilities (L7471–L7780)

| # | File | Lines | Size |
|---|------|-------|------|
| 62 | `espn_service/apps/core/__init__.py` | 7471–7479 | 9 |
| 63 | `espn_service/apps/core/apps.py` | 7480–7498 | 19 |
| 64 | `espn_service/apps/core/exceptions.py` | 7499–7636 | 138 |
| 65 | `espn_service/apps/core/middleware.py` | 7637–7716 | 80 |
| 66 | `espn_service/apps/core/views.py` | 7717–7780 | 64 |

## ESPN Service — Django Config (L13098–L13775)

| # | File | Lines | Size |
|---|------|-------|------|
| 67 | `espn_service/config/__init__.py` | 13098–13110 | 13 |
| 68 | `espn_service/config/asgi.py` | 13111–13127 | 17 |
| 69 | `espn_service/config/celery.py` | 13128–13158 | 31 |
| 70 | `espn_service/config/settings/__init__.py` | 13159–13167 | 9 |
| 71 | `espn_service/config/settings/base.py` | 13168–13521 | 354 |
| 72 | `espn_service/config/settings/local.py` | 13522–13567 | 46 |
| 73 | `espn_service/config/settings/production.py` | 13568–13660 | 93 |
| 74 | `espn_service/config/settings/test.py` | 13661–13717 | 57 |
| 75 | `espn_service/config/urls.py` | 13718–13758 | 41 |
| 76 | `espn_service/config/wsgi.py` | 13759–13775 | 17 |

## ESPN Service — Build & Deploy (L6649–L14228)

| # | File | Lines | Size |
|---|------|-------|------|
| 77 | `espn_service/.env.example` | 6649–6685 | 37 |
| 78 | `espn_service/.gitignore` | 6686–6835 | 150 |
| 79 | `espn_service/.pre-commit-config.yaml` | 6836–6882 | 47 |
| 80 | `espn_service/Dockerfile` | 6883–6945 | 63 |
| 81 | `espn_service/Makefile` | 6946–7087 | 142 |
| 82 | `espn_service/apps/__init__.py` | 7462–7470 | 9 |
| 83 | `espn_service/conftest.py` | 13776–13787 | 12 |
| 84 | `espn_service/docker-compose.prod.yml` | 13788–13877 | 90 |
| 85 | `espn_service/docker-compose.test.yml` | 13878–13926 | 49 |
| 86 | `espn_service/docker-compose.yml` | 13927–14033 | 107 |
| 87 | `espn_service/manage.py` | 14034–14063 | 30 |
| 88 | `espn_service/pyproject.toml` | 14064–14228 | 165 |

## ESPN Service — Tests (L14229–L16814)

| # | File | Lines | Size |
|---|------|-------|------|
| 89 | `espn_service/tests/__init__.py` | 14229–14237 | 9 |
| 90 | `espn_service/tests/conftest.py` | 14238–14556 | 319 |
| 91 | `espn_service/tests/test_api.py` | 14557–15007 | 451 |
| 92 | `espn_service/tests/test_espn_client.py` | 15008–15440 | 433 |
| 93 | `espn_service/tests/test_espn_client_new_methods.py` | 15441–15792 | 352 |
| 94 | `espn_service/tests/test_ingest_all_teams.py` | 15793–15918 | 126 |
| 95 | `espn_service/tests/test_ingestion.py` | 15919–16197 | 279 |
| 96 | `espn_service/tests/test_ingestion_new.py` | 16198–16604 | 407 |
| 97 | `espn_service/tests/test_models.py` | 16605–16814 | 210 |

## NHL Service — API Client (L17853–L17937)

| # | File | Lines | Size |
|---|------|-------|------|
| 98 | `nhl_service/clients/nhl_client.py` | 17853–17937 | 85 |

## NHL Service — Models & Ingestion (L16986–L17852)

| # | File | Lines | Size |
|---|------|-------|------|
| 99 | `nhl_service/apps/__init__.py` | 16986–16994 | 9 |
| 100 | `nhl_service/apps/ingest/__init__.py` | 16995–17003 | 9 |
| 101 | `nhl_service/apps/ingest/apps.py` | 17004–17020 | 17 |
| 102 | `nhl_service/apps/ingest/tasks.py` | 17021–17223 | 203 |
| 103 | `nhl_service/apps/nhl/admin.py` | 17224–17283 | 60 |
| 104 | `nhl_service/apps/nhl/apps.py` | 17284–17300 | 17 |
| 105 | `nhl_service/apps/nhl/migrations/0001_initial.py` | 17301–17547 | 247 |
| 106 | `nhl_service/apps/nhl/migrations/__init__.py` | 17548–17555 | 8 |
| 107 | `nhl_service/apps/nhl/models.py` | 17556–17694 | 139 |
| 108 | `nhl_service/apps/nhl/serializers.py` | 17695–17776 | 82 |
| 109 | `nhl_service/apps/nhl/views.py` | 17777–17852 | 76 |

## NHL Service — Django Config (L17938–L18291)

| # | File | Lines | Size |
|---|------|-------|------|
| 110 | `nhl_service/config/__init__.py` | 17938–17946 | 9 |
| 111 | `nhl_service/config/asgi.py` | 17947–17963 | 17 |
| 112 | `nhl_service/config/celery.py` | 17964–17982 | 19 |
| 113 | `nhl_service/config/settings/__init__.py` | 17983–17991 | 9 |
| 114 | `nhl_service/config/settings/base.py` | 17992–18152 | 161 |
| 115 | `nhl_service/config/settings/local.py` | 18153–18186 | 34 |
| 116 | `nhl_service/config/settings/production.py` | 18187–18207 | 21 |
| 117 | `nhl_service/config/settings/test.py` | 18208–18241 | 34 |
| 118 | `nhl_service/config/urls.py` | 18242–18274 | 33 |
| 119 | `nhl_service/config/wsgi.py` | 18275–18291 | 17 |

## NHL Service — Build & Deploy (L16815–L18556)

| # | File | Lines | Size |
|---|------|-------|------|
| 120 | `nhl_service/.env.example` | 16815–16842 | 28 |
| 121 | `nhl_service/.gitignore` | 16843–16887 | 45 |
| 122 | `nhl_service/Dockerfile` | 16888–16940 | 53 |
| 123 | `nhl_service/Makefile` | 16941–16985 | 45 |
| 124 | `nhl_service/docker-compose.yml` | 18292–18360 | 69 |
| 125 | `nhl_service/manage.py` | 18361–18391 | 31 |
| 126 | `nhl_service/pyproject.toml` | 18392–18556 | 165 |

## NHL Service — Tests (L18557–L18617)

| # | File | Lines | Size |
|---|------|-------|------|
| 127 | `nhl_service/tests/__init__.py` | 18557–18565 | 9 |
| 128 | `nhl_service/tests/conftest.py` | 18566–18590 | 25 |
| 129 | `nhl_service/tests/test_models.py` | 18591–18617 | 27 |

---

## Quick Reference — Sport Docs Cheat Sheet

| Sport | Slug | Leagues | Lines | Size |
|-------|------|---------|-------|------|
| Global/Cross-Sport | `—` | all | 2598–3140 | 543 |
| Australian Football | `australian-football` | 1 | 3141–3300 | 160 |
| Baseball | `baseball` | 13 | 3301–3519 | 219 |
| Basketball | `basketball` | 15 | 3520–3792 | 273 |
| College Sports | `various` | varies | 3793–3957 | 165 |
| Cricket | `cricket` | varies | 3958–4108 | 151 |
| Field Hockey | `field-hockey` | 1 | 4109–4252 | 144 |
| Football | `football` | 5 | 4253–4530 | 278 |
| Golf | `golf` | 9 | 4531–4695 | 165 |
| Hockey | `hockey` | 6 | 4696–4905 | 210 |
| Lacrosse | `lacrosse` | 4 | 4906–5055 | 150 |
| MMA | `mma` | 25+ | 5056–5230 | 175 |
| Racing | `racing` | 5 | 5231–5382 | 152 |
| Rugby | `rugby` | 24 | 5383–5539 | 157 |
| Rugby League | `rugby-league` | 1 | 5540–5699 | 160 |
| Soccer | `soccer` | 260+ | 5700–6200 | 501 |
| Tennis | `tennis` | varies | 6201–6358 | 158 |
| Volleyball | `volleyball` | varies | 6359–6503 | 145 |
| Water Polo | `water-polo` | varies | 6504–6648 | 145 |

---

## Key ESPN API Domains (Quick Ref)

| Domain | Purpose |
|--------|---------|
| `site.api.espn.com` | Scores, news, teams, standings (v2 & v3) |
| `sports.core.api.espn.com` | Athletes, stats, odds, detailed data (v2 & v3) |
| `site.web.api.espn.com` | Search, athlete profiles, standings |
| `cdn.espn.com` | CDN-optimized live data (use `xhr=1`) |
| `fantasy.espn.com` | Fantasy sports leagues |
| `now.core.api.espn.com` | Real-time news feeds |

## Common URL Pattern

```
# Site API (general)
https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/{resource}

# Core API (detailed)
https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/{resource}

# CDN (live/fast)
https://cdn.espn.com/core/{league}/{resource}?xhr=1
```

