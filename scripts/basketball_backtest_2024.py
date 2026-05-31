"""NBA 2024 sezonu backtest — model_p vs gerçek sonuç.

Plan 1.C son adımı. Hedef: ≥%66 moneyline doğruluk (FiveThirtyEight referans).

Akış:
  1. nba_api üzerinden 2024 regular season game-log çek
  2. Tarihsel sırayla maçları işle (data leakage yok)
  3. Her maç başında: önceki maçlardan Elo + Efficiency hesapla
  4. Model_p (moneyline) üret, gerçek sonuçla karşılaştır
  5. Brier score + accuracy raporla

Çıktı:
  - Toplam maç sayısı, doğru tahmin sayısı, accuracy
  - Brier score (düşük iyidir, 0.25 = rastgele)
  - Eşik kontrolü: ≥%66 → PASS, altı → BELOW THRESHOLD (kalibrasyon revize)
"""
from __future__ import annotations

import sys
from collections import defaultdict

try:
    from nba_api.stats.endpoints import leaguegamelog
except ImportError:
    print("ERROR: nba_api paketi yüklü değil")
    sys.exit(2)

from src.domain.pricing.basketball.efficiency_metrics import (
    compute_team_efficiency,
)
from src.domain.pricing.basketball.match_pricer import compute_market_anchor
from src.domain.pricing.basketball.team_elo import EloRating, update_elo
from src.infrastructure.data.basketball.nba_api_refresher import (
    fetch_game_log_via_nba_api,
)
from src.infrastructure.data.basketball.schemas import GameRecord


HOME_ADVANTAGE = 100.0
K_FACTOR = 20.0
BLEND_ELO = 0.55
MIN_GAMES_BEFORE_PREDICT = 10   # Erken sezonda rating volatile


def main() -> int:
    print("[BACKTEST] Fetching NBA 2024 regular season game log...")
    games = fetch_game_log_via_nba_api(
        league="nba", season="2024",
        endpoint_factory=lambda **kwargs: leaguegamelog.LeagueGameLog(
            season=kwargs["season"], league_id=kwargs["league_id"],
            season_type_all_star="Regular Season",
        ),
    )
    if not games:
        print("[BACKTEST] FAIL: zero games fetched")
        return 1
    print(f"[BACKTEST] Fetched {len(games)} games")
    games.sort(key=lambda g: g.game_date_utc)

    elo: dict[str, EloRating] = defaultdict(EloRating)
    history: list[GameRecord] = []
    correct = 0
    total = 0
    brier_sum = 0.0

    for g in games:
        home_elo = elo[g.home_team]
        away_elo = elo[g.away_team]
        home_eff = compute_team_efficiency(history, g.home_team)
        away_eff = compute_team_efficiency(history, g.away_team)
        eligible = (
            home_elo.games >= MIN_GAMES_BEFORE_PREDICT
            and away_elo.games >= MIN_GAMES_BEFORE_PREDICT
            and home_eff is not None and away_eff is not None
        )
        if eligible:
            p_home_win = compute_market_anchor(
                market_type="moneyline",
                home_elo=home_elo, away_elo=away_elo,
                home_eff=home_eff, away_eff=away_eff,
                home_advantage=HOME_ADVANTAGE, blend_elo=BLEND_ELO, line=None,
            )
            if p_home_win is not None:
                actual = 1.0 if g.home_score > g.away_score else 0.0
                pred = 1 if p_home_win > 0.5 else 0
                if (pred == 1 and actual == 1) or (pred == 0 and actual == 0):
                    correct += 1
                brier_sum += (p_home_win - actual) ** 2
                total += 1
        home_won = g.home_score > g.away_score
        new_home, new_away = update_elo(
            home_elo, away_elo, home_won=home_won,
            k_factor=K_FACTOR, home_advantage=HOME_ADVANTAGE,
        )
        elo[g.home_team] = new_home
        elo[g.away_team] = new_away
        history.append(g)

    if total == 0:
        print("[BACKTEST] FAIL: no eligible predictions")
        return 1
    accuracy = correct / total
    brier = brier_sum / total
    print(f"[BACKTEST] Predictions: {total}/{len(games)}")
    print(f"[BACKTEST] Correct: {correct} ({accuracy:.1%})")
    print(f"[BACKTEST] Brier score: {brier:.4f} (0.25=random, lower=better)")
    threshold = 0.66
    if accuracy >= threshold:
        print(f"[BACKTEST] PASS - accuracy {accuracy:.1%} >= {threshold:.0%}")
        return 0
    print(f"[BACKTEST] BELOW THRESHOLD - accuracy {accuracy:.1%} < {threshold:.0%}")
    print("[BACKTEST] Recommendation: kalibrasyon egrisi ve/veya home_advantage tuning")
    return 0  # backtest sonucu raporlanır, exit 0 (failure değil, bilgi)


if __name__ == "__main__":
    sys.exit(main())
