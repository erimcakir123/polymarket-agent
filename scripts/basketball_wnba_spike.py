"""WNBA veri kalitesi spike testi — Faz 1 kapsam kararı.

Son 1 WNBA sezonu için nba_api üzerinden game-log çek.
Maç sayısı + kolon dolgunluğu + takım kapsamı raporla.

Eşik (Plan 1.A başlangıç onayı):
  - ≥ %90 sezon maçı kapsama
  - Tüm 12 WNBA takımı görünmeli
  - Possessions hesabı için kolonlar dolu olmalı

Geçerse → WNBA Faz 1'e dahil edilir (config.basketball.enabled_leagues).
Geçmezse → TODO.md'ye "wnba-deferred" eklenir, sonraki faza ertelenir.
"""
from __future__ import annotations

import sys
from collections import Counter

try:
    from nba_api.stats.endpoints import leaguegamelog
except ImportError:
    print("ERROR: nba_api paketi yüklü değil. `pip install -r requirements.txt`")
    sys.exit(2)

from src.infrastructure.data.basketball.nba_api_refresher import (
    fetch_game_log_via_nba_api,
)


def main():
    print("[WNBA SPIKE] Fetching 2024 season game log via nba_api...")
    try:
        games = fetch_game_log_via_nba_api(
            league="wnba",
            season="2024",
            endpoint_factory=lambda **kwargs: leaguegamelog.LeagueGameLog(
                season=kwargs["season"],
                league_id=kwargs["league_id"],
                season_type_all_star="Regular Season",
            ),
        )
    except Exception as exc:
        print(f"ERROR fetching: {exc}")
        sys.exit(3)
    print(f"[WNBA SPIKE] Fetched {len(games)} games")
    if not games:
        print("[WNBA SPIKE] FAIL — sıfır maç, WNBA Faz 1 dışı")
        sys.exit(1)
    teams: Counter[str] = Counter()
    for g in games:
        teams[g.home_team] += 1
        teams[g.away_team] += 1
    expected_teams = 12
    expected_min_games = int(40 * 0.9)  # ~36, regular season 40 maç/takım
    print(f"[WNBA SPIKE] Unique teams: {len(teams)} (expected {expected_teams})")
    print(f"[WNBA SPIKE] Team match counts: {dict(teams)}")
    if len(teams) < expected_teams:
        print("[WNBA SPIKE] FAIL — takım sayısı yetersiz, WNBA Faz 1 dışı")
        sys.exit(1)
    short_teams = [t for t, c in teams.items() if c < expected_min_games]
    if short_teams:
        print(f"[WNBA SPIKE] WARN — bu takımların maç sayısı düşük: {short_teams}")
    print("[WNBA SPIKE] PASS — WNBA Faz 1 kapsama eklenebilir")


if __name__ == "__main__":
    main()
