"""Enrich fail taksonomisi — odds_enricher sonucu için yapılandırılmış dönüş.

SPEC-001 (moneyline taksonomi) + SPEC-K (spread/totals metadata).
Domain katmanı — I/O yok, saf data class'ları.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from src.domain.analysis.probability import BookmakerProbability

if TYPE_CHECKING:
    from src.models.enums import TotalSide


class EnrichFailReason(str, Enum):
    """Odds API enrichment sırasında başarısız olunan adım."""
    SPORT_KEY_UNRESOLVED = "sport_key_unresolved"
    TEAM_EXTRACT_FAILED = "team_extract_failed"
    EMPTY_EVENTS = "empty_events"
    EVENT_NO_MATCH = "event_no_match"
    EMPTY_BOOKMAKERS = "empty_bookmakers"
    # SPEC-K: bookmaker spread/totals köprüsü
    BOOKMAKER_NO_SPREAD = "bookmaker_no_spread"
    BOOKMAKER_NO_TOTALS = "bookmaker_no_totals"


@dataclass(frozen=True)
class EnrichResult:
    """enrich_market sonucu — ya probability dolu ya fail_reason.

    SPEC-K: spread/totals market'leri için ek metadata. Moneyline'da hepsi None.
    """
    probability: BookmakerProbability | None
    fail_reason: EnrichFailReason | None
    spread_line: float | None = None
    total_line: float | None = None
    total_side: "TotalSide | None" = None
