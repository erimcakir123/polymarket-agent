"""Enrich fail taksonomisi — odds_enricher sonucu için yapılandırılmış dönüş.

SPEC-001 (moneyline taksonomi).
Domain katmanı — I/O yok, saf data class'ları.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.domain.analysis.probability import BookmakerProbability


class EnrichFailReason(str, Enum):
    """Odds API + tennis model enrichment sırasında başarısız olunan adım."""
    SPORT_KEY_UNRESOLVED = "sport_key_unresolved"
    TEAM_EXTRACT_FAILED = "team_extract_failed"
    EMPTY_EVENTS = "empty_events"
    EVENT_NO_MATCH = "event_no_match"
    EMPTY_BOOKMAKERS = "empty_bookmakers"
    # Tennis model anchor (Adım 3-5):
    MODEL_PLAYER_NOT_IN_RATINGS = "model_player_not_in_ratings"
    MODEL_DATA_MISSING = "model_data_missing"  # surface yok, line/handicap parse fail
    MODEL_MARKET_UNSUPPORTED = "model_market_unsupported"
    # 2026-06-11: zemin bazlı model-ML kapatma (çim kararı — config
    # tennis.model_ml_disabled_surfaces). Bahisçi yolu etkilenmez.
    MODEL_SURFACE_DISABLED = "model_surface_disabled"
    # Basketball model anchor (Plan 1.C):
    MODEL_TEAM_NOT_IN_RATINGS = "model_team_not_in_ratings"
    MODEL_BASKETBALL_DATA_MISSING = "model_basketball_data_missing"


@dataclass(frozen=True)
class EnrichResult:
    """enrich_market sonucu — ya probability dolu ya fail_reason."""
    probability: BookmakerProbability | None
    fail_reason: EnrichFailReason | None
