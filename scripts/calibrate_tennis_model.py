"""Tennis model calibration — walk-forward holdout test.

Yöntem:
1. Tüm maçları tarihe göre sırala.
2. Maç M_t için: M_0..M_{t-1}'i kullan → rating + serve stats üret.
3. M_t için modelin h2h tahminini hesapla.
4. Gerçek sonuçla karşılaştır (winner kazandı = 1).
5. n_bins reliability diagram fit et.
6. data/tennis_calibration.json'a kaydet.

Walk-forward gerçek out-of-sample test verir. Tam çalışması büyük data
setlerinde uzun sürer (60K+ maç × Glicko update). Optimization: snapshot
update interval (her N maçta bir tam fit yerine incremental update).

Bu script production wiring değil — kanıt üretir. Sonuç kullanıcıya rapor.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

from src.domain.pricing.tennis.calibration import fit_calibration
from src.domain.pricing.tennis.glicko import Rating, update_rating, win_probability
from src.domain.pricing.tennis.serve_metrics import (
    PlayerServeStats,
    point_win_on_serve,
)
from src.domain.pricing.tennis.markov import match_win_prob, set_win_prob
from src.infrastructure.data.calibration_store import save_calibration
from src.infrastructure.data.sackmann_csv_loader import load_matches_from_path

logger = logging.getLogger(__name__)

_DEFAULT_CACHE_DIR = Path("data/sackmann_cache")
_DEFAULT_OUTPUT = Path("data/tennis_calibration.json")
_MIN_HISTORY = 1000  # ilk N maç sadece training (predict skip)
_N_BINS = 10


def _predict_h2h(
    a_rating: Rating,
    b_rating: Rating,
    a_serve: PlayerServeStats | None,
    b_serve: PlayerServeStats | None,
    best_of: int,
    glicko_weight: float,
) -> float:
    glicko_p = win_probability(a_rating, b_rating)
    if a_serve is None or b_serve is None:
        return glicko_p
    p_a = point_win_on_serve(a_serve, b_serve)
    p_b = point_win_on_serve(b_serve, a_serve)
    set_p = set_win_prob(p_a, p_b)
    serve_p = match_win_prob(set_p, best_of=best_of)
    return glicko_weight * glicko_p + (1.0 - glicko_weight) * serve_p


def _update_serve(stats: dict, key: tuple[str, str], pts_won: int, pts_total: int,
                  ret_won: int, ret_total: int) -> None:
    if key not in stats:
        stats[key] = [0, 0, 0, 0]  # serve_won, serve_total, return_won, return_total
    stats[key][0] += pts_won
    stats[key][1] += pts_total
    stats[key][2] += ret_won
    stats[key][3] += ret_total


def _stats_to_serve(raw: list[int]) -> PlayerServeStats:
    s_pct = raw[0] / raw[1] if raw[1] > 0 else 0.6
    r_pct = raw[2] / raw[3] if raw[3] > 0 else 0.35
    return PlayerServeStats(s_pct, r_pct, raw[1] + raw[3])


def calibrate_h2h(
    cache_dir: Path,
    output_path: Path,
    glicko_weight: float = 0.6,
) -> None:
    csv_files = sorted(Path(cache_dir).glob("*.csv"))
    all_matches = []
    for csv in csv_files:
        try:
            all_matches.extend(load_matches_from_path(csv))
        except OSError as exc:
            logger.warning("CSV load failed: %s (%s)", csv, exc)
    all_matches.sort(key=lambda m: m.tourney_date)
    logger.info("Walk-forward calibration on %d matches", len(all_matches))

    ratings: dict[str, Rating] = defaultdict(Rating)
    serve_stats: dict[tuple[str, str], list[int]] = {}
    predictions: list[float] = []
    outcomes: list[int] = []

    for i, m in enumerate(all_matches):
        if i >= _MIN_HISTORY:
            a_rating = ratings[m.winner_name]
            b_rating = ratings[m.loser_name]
            a_serve_raw = serve_stats.get((m.winner_name, m.surface))
            b_serve_raw = serve_stats.get((m.loser_name, m.surface))
            a_serve = _stats_to_serve(a_serve_raw) if a_serve_raw else None
            b_serve = _stats_to_serve(b_serve_raw) if b_serve_raw else None
            p_a_wins = _predict_h2h(
                a_rating, b_rating, a_serve, b_serve, m.best_of, glicko_weight,
            )
            predictions.append(p_a_wins)
            outcomes.append(1)  # winner truly won

        # Update with this match (training data going forward)
        w = ratings[m.winner_name]
        loser_r = ratings[m.loser_name]
        ratings[m.winner_name] = update_rating(w, [loser_r], [1.0])
        ratings[m.loser_name] = update_rating(loser_r, [w], [0.0])

        w_won = m.w_1st_won + m.w_2nd_won
        l_won = m.l_1st_won + m.l_2nd_won
        _update_serve(serve_stats, (m.winner_name, m.surface),
                      w_won, m.w_svpt, m.l_svpt - l_won, m.l_svpt)
        _update_serve(serve_stats, (m.loser_name, m.surface),
                      l_won, m.l_svpt, m.w_svpt - w_won, m.w_svpt)

        if (i + 1) % 10000 == 0:
            logger.info("Progress: %d/%d", i + 1, len(all_matches))

    logger.info("Generated %d predictions for calibration fit", len(predictions))
    # Reliability: bot her zaman P(winner wins). Outcome zaten 1.
    # Daha doğru kalibre için RANDOM PERSPECTIVE gerek — A her zaman winner alır,
    # bu durumda calibration bias'lı olur. Düzeltme: yarısında perspective swap.
    swapped_predictions = []
    swapped_outcomes = []
    for i, (p, o) in enumerate(zip(predictions, outcomes)):
        if i % 2 == 0:
            swapped_predictions.append(p)
            swapped_outcomes.append(o)
        else:
            swapped_predictions.append(1.0 - p)
            swapped_outcomes.append(0)

    curve = fit_calibration(swapped_predictions, swapped_outcomes, n_bins=_N_BINS)
    save_calibration({"moneyline": curve}, output_path)
    logger.info("Saved calibration curve to %s", output_path)
    for mid, obs in zip(curve.bin_midpoints, curve.bin_observed):
        logger.info("  bin mid=%.2f → observed=%.3f", mid, obs)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    calibrate_h2h(_DEFAULT_CACHE_DIR, _DEFAULT_OUTPUT)


if __name__ == "__main__":
    main()
