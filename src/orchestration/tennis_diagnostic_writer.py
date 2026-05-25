"""Tennis candidate diagnostic logging — feature resolve + tier classify + log record.

Extracted from tennis_agent.run_one_cycle (2026-05-26 ARCH_GUARD compliance pass)
to keep tennis_agent.py under the 400-line limit. Sole caller is tennis_agent.

Single responsibility: for one EdgeCandidate + MarketData pair, look up player
ratings (tour-scoped), extract Sackmann match features, classify confidence tier
via the enricher's classify_tier, and emit a TennisDiagnosticLogger prediction
record. Returns (did_log, tier) so the caller decides whether to size + submit
an entry signal.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from src.config.settings import AppConfig
from src.domain.matching.tennis_player_matcher import build_match_index, match_player
from src.domain.prediction.feature_extractor import extract_features
from src.domain.prediction.tennis_predictor import MarketPrediction
from src.infrastructure.data.sackmann_csv_client import SackmannMatch
from src.infrastructure.data.tennis_ratings_store import PlayerRating
from src.models.market import MarketData
from src.orchestration.tennis_diagnostic_logger import TennisDiagnosticLogger
from src.strategy.enrichment.tennis_market_enricher import classify_tier
from src.strategy.entry.tennis_entry import EdgeCandidate


def log_candidate(
    candidate: EdgeCandidate,
    market: MarketData,
    parsed: dict,
    ratings: dict[str, PlayerRating],
    sackmann_matches: list[SackmannMatch],
    cfg: AppConfig,
    diagnostic_logger: TennisDiagnosticLogger,
    now: datetime,
) -> tuple[bool, str]:
    """Resolve features + tier for one candidate and write diagnostic log record.

    Returns (did_log, tier) — tier is "A" / "B" / "skip" / "" (player not found).
    Caller uses tier to decide whether to size + submit an entry signal.

    Name-match indexes are rebuilt per call scoped to parsed["tour"] (small
    dicts; cross-tour caching is unsafe — see enricher note).
    """
    tour = parsed["tour"]
    by_full, by_last = build_match_index(ratings, tour=tour)
    p1_rating = match_player(parsed["p1_name"], ratings, by_full=by_full, by_last=by_last, tour=tour)
    p2_rating = match_player(parsed["p2_name"], ratings, by_full=by_full, by_last=by_last, tour=tour)
    if p1_rating is None or p2_rating is None:
        return False, ""

    features = extract_features(
        matches=sackmann_matches,
        p1=p1_rating.player_name,
        p2=p2_rating.player_name,
        surface=parsed["surface"].capitalize(),
        snapshot_date=now,
    )
    tier = classify_tier(features, cfg)
    if tier == "skip":
        return False, tier

    direction = "BUY_YES" if candidate.edge >= 0 else "BUY_NO"
    prediction = MarketPrediction(
        market_type=candidate.market_type,
        probability=candidate.model_p,
        raw_probability=candidate.model_p,
        notes=f"edge={candidate.edge:+.3f} tier={tier}",
    )
    tournament = market.question.split(":")[0].strip() if ":" in market.question else "Unknown"

    diagnostic_logger.log_prediction(
        trade_id=str(uuid.uuid4()),
        tournament=tournament,
        tournament_tier="unknown",
        slug=market.slug or "",
        format_="BO3",
        match_start_iso=market.match_start_iso or now.isoformat() + "Z",
        market_polymarket_price=market.yes_price,
        direction=direction,
        prediction=prediction,
        features=features,
        confidence_tier=tier,
        edge=candidate.edge,
    )
    return True, tier
