"""Tennis market'ler için model-anchored enrichment.

Sport_tag tennis ise odds_enricher (bookmaker h2h) yerine bu modül çağrılır.
Model çıktısı BookmakerProbability'ye sarılır — confidence grading mevcut
pipeline ile uyumlu kalır.

Model çıktısının "kalitesi" num_bookmakers=2, has_sharp=False olarak
modellenir → B confidence. A-only entry modunda bot trade yapmaz; calibration
curve (Adım 4) sonrası kanıt geldikçe artırılır.
"""
from __future__ import annotations

from src.domain.analysis.enrich_outcome import EnrichFailReason, EnrichResult
from src.domain.analysis.probability import calculate_bookmaker_probability
from src.domain.pricing.tennis.player_snapshot import PlayerSnapshot
from src.strategy.enrichment.tennis_model_anchor import compute_model_anchor

_MODEL_EQUIV_BOOKMAKERS = 2.0
_MODEL_HAS_SHARP = False


def enrich_tennis_from_model(
    player_a: str,
    player_b: str,
    market_type: str,
    surface: str,
    best_of: int,
    ratings: dict[str, PlayerSnapshot],
    line: float | None = None,
    handicap: float | None = None,
) -> EnrichResult:
    """Tennis market → model probability → EnrichResult.

    Eksik oyuncu, eksik veri veya bilinmeyen market → fail_reason.
    """
    a_snap = ratings.get(player_a)
    b_snap = ratings.get(player_b)
    if a_snap is None or b_snap is None:
        return EnrichResult(probability=None, fail_reason=EnrichFailReason.EVENT_NO_MATCH)

    model_p = compute_model_anchor(
        market_type=market_type,
        a_snapshot=a_snap,
        b_snapshot=b_snap,
        surface=surface,
        best_of=best_of,
        line=line,
        handicap=handicap,
    )
    if model_p is None:
        return EnrichResult(probability=None, fail_reason=EnrichFailReason.EMPTY_BOOKMAKERS)

    prob = calculate_bookmaker_probability(
        bookmaker_prob=model_p,
        num_bookmakers=_MODEL_EQUIV_BOOKMAKERS,
        has_sharp=_MODEL_HAS_SHARP,
    )
    return EnrichResult(probability=prob, fail_reason=None)
