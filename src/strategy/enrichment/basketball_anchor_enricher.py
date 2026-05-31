"""Basketball market'ler için model-anchored enrichment.

Sport_tag basketball ise odds_enricher (bookmaker h2h) yerine bu modül çağrılır.
Tennis_anchor_enricher pattern'inin birebir kopyası (Plan 1.C Task 3 + 1.D Task 3+5).

Akış:
  1. ratings + efficiencies eksik → fail_reason
  2. compute_model_anchor → ham model_p
  3. calibration_curves["{league}:{market_type}"] varsa apply_calibration
  4. cliprange [%5, %95] güvenlik kemeri (Plan 1.D)
  5. calculate_bookmaker_probability sarmal → A confidence

Calibration eğrisi key biçimi "{league}:{market_type}" — örn "nba:moneyline",
"wnba:totals". Lig-başına ayrı kalibrasyon (NBA vs WNBA hücum profili farklı).
"""
from __future__ import annotations

from typing import Optional

from src.domain.analysis.enrich_outcome import EnrichFailReason, EnrichResult
from src.domain.analysis.probability import calculate_bookmaker_probability
from src.domain.calibration.curve import CalibrationCurve, apply_calibration
from src.domain.calibration.sanity import cliprange
from src.domain.pricing.basketball.pace_efficiency import TeamEfficiency
from src.domain.pricing.basketball.team_elo import EloRating
from src.strategy.enrichment.basketball_model_anchor import compute_model_anchor

_MODEL_EQUIV_BOOKMAKERS = 5.0
_MODEL_HAS_SHARP = True


def enrich_basketball_from_model(
    home_team: str, away_team: str,
    market_type: str, league: str,
    ratings: dict[str, EloRating],
    efficiencies: dict[str, TeamEfficiency],
    home_advantage: float, blend_elo: float,
    line: Optional[float] = None,
    calibration_curves: Optional[dict[str, CalibrationCurve]] = None,
) -> EnrichResult:
    """Basketball market → model probability → EnrichResult.

    Eksik takım veya eksik veri → fail_reason. Calibration eğrisi varsa
    "{league}:{market_type}" anahtarı kullanılır. Son adımda cliprange
    güvenlik kemeri ile P(YES) [%5, %95] aralığına kırpılır.
    """
    home_elo = ratings.get(home_team)
    away_elo = ratings.get(away_team)
    if home_elo is None or away_elo is None:
        return EnrichResult(
            probability=None,
            fail_reason=EnrichFailReason.MODEL_TEAM_NOT_IN_RATINGS,
        )
    home_eff = efficiencies.get(home_team)
    away_eff = efficiencies.get(away_team)
    if home_eff is None or away_eff is None:
        return EnrichResult(
            probability=None,
            fail_reason=EnrichFailReason.MODEL_BASKETBALL_DATA_MISSING,
        )
    model_p = compute_model_anchor(
        market_type=market_type,
        home_elo=home_elo, away_elo=away_elo,
        home_eff=home_eff, away_eff=away_eff,
        home_advantage=home_advantage, blend_elo=blend_elo, line=line,
    )
    if model_p is None:
        return EnrichResult(
            probability=None,
            fail_reason=EnrichFailReason.MODEL_BASKETBALL_DATA_MISSING,
        )
    if calibration_curves:
        key = f"{league.lower()}:{market_type.lower()}"
        curve = calibration_curves.get(key)
        if curve is not None:
            model_p = apply_calibration(model_p, curve)
    model_p = cliprange(model_p)
    prob = calculate_bookmaker_probability(
        bookmaker_prob=model_p,
        num_bookmakers=_MODEL_EQUIV_BOOKMAKERS,
        has_sharp=_MODEL_HAS_SHARP,
        source="model",
    )
    return EnrichResult(probability=prob, fail_reason=None)
