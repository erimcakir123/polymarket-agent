"""Enrich fail taksonomisi — odds_enricher sonucu için yapılandırılmış dönüş.

SPEC-001. Domain katmanı — I/O yok, saf data class'ları.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.domain.analysis.probability import BookmakerProbability


class EnrichFailReason(str, Enum):
    """Odds API enrichment sırasında başarısız olunan adım."""
    SPORT_KEY_UNRESOLVED = "sport_key_unresolved"
    TEAM_EXTRACT_FAILED = "team_extract_failed"
    EMPTY_EVENTS = "empty_events"
    EVENT_NO_MATCH = "event_no_match"
    EMPTY_BOOKMAKERS = "empty_bookmakers"


@dataclass(frozen=True)
class EnrichResult:
    """enrich_market sonucu — ya probability dolu ya fail_reason."""
    probability: BookmakerProbability | None
    fail_reason: EnrichFailReason | None
    odds_commence_time: str = ""
