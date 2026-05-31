"""Tennis market'ler için model-anchored enrichment.

Sport_tag tennis ise odds_enricher (bookmaker h2h) yerine bu modül çağrılır.
Model çıktısı BookmakerProbability'ye sarılır — confidence grading mevcut
pipeline ile uyumlu kalır.

Confidence: kullanıcı kararı 2026-05-31 — Sackmann modeli sharp-equivalent
sayılır (PLOS One 2022 %73 doğruluk). num_bookmakers=5, has_sharp=True →
A confidence (canlı trade aktif). Adım 4 kalibrasyon sonrası kanıta göre
revize edilir.
"""
from __future__ import annotations

from src.domain.analysis.enrich_outcome import EnrichFailReason, EnrichResult
from src.domain.analysis.probability import calculate_bookmaker_probability
from src.domain.pricing.tennis.calibration import CalibrationCurve, apply_calibration
from src.domain.pricing.tennis.player_snapshot import PlayerSnapshot
from src.strategy.enrichment.tennis_model_anchor import compute_model_anchor

_MODEL_EQUIV_BOOKMAKERS = 5.0
_MODEL_HAS_SHARP = True


def enrich_tennis_from_model(
    player_a: str,
    player_b: str,
    market_type: str,
    surface: str,
    best_of: int,
    ratings: dict[str, PlayerSnapshot],
    calibration_curves: dict[str, CalibrationCurve] | None = None,
    line: float | None = None,
    handicap: float | None = None,
    glicko_weight: float = 0.6,
) -> EnrichResult:
    """Tennis market → model probability → calibration → EnrichResult.

    Eksik oyuncu, eksik veri veya bilinmeyen market → fail_reason.
    Calibration curve verilirse model çıktısı eğriyle düzeltilir.
    """
    a_snap = ratings.get(player_a)
    b_snap = ratings.get(player_b)
    if a_snap is None or b_snap is None:
        return EnrichResult(
            probability=None,
            fail_reason=EnrichFailReason.MODEL_PLAYER_NOT_IN_RATINGS,
        )

    model_p = compute_model_anchor(
        market_type=market_type,
        a_snapshot=a_snap,
        b_snapshot=b_snap,
        surface=surface,
        best_of=best_of,
        line=line,
        handicap=handicap,
        glicko_weight=glicko_weight,
    )
    if model_p is None:
        return EnrichResult(probability=None, fail_reason=EnrichFailReason.MODEL_DATA_MISSING)

    if calibration_curves:
        curve = calibration_curves.get(market_type.lower())
        if curve is not None:
            model_p = apply_calibration(model_p, curve)

    prob = calculate_bookmaker_probability(
        bookmaker_prob=model_p,
        num_bookmakers=_MODEL_EQUIV_BOOKMAKERS,
        has_sharp=_MODEL_HAS_SHARP,
        source="model",
    )
    return EnrichResult(probability=prob, fail_reason=None)
