"""Odds API canlı skor istemcisi (SPEC-004 Bileşen 1).

/v4/sports/{sport}/scores endpoint'inden canlı skor çeker.
Mevcut OddsAPIClient'ın HTTP altyapısını kullanır.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from src.infrastructure.apis.odds_client import OddsAPIClient

logger = logging.getLogger(__name__)


@dataclass
class MatchScore:
    """Tek bir maçın canlı skor bilgisi."""

    event_id: str
    home_team: str
    away_team: str
    home_score: int | None  # None = maç başlamadı
    away_score: int | None
    period: str  # "1st", "2nd", "3rd", "OT", "Final", ""
    is_completed: bool
    last_updated: str  # ISO timestamp


def _parse_scores(raw: list[dict]) -> list[MatchScore]:
    """Odds API /scores response'unu MatchScore listesine çevir."""
    result: list[MatchScore] = []
    for event in raw:
        scores = event.get("scores")
        home_score: int | None = None
        away_score: int | None = None
        if scores and isinstance(scores, list):
            for s in scores:
                name = s.get("name", "")
                score_val = s.get("score")
                if score_val is not None:
                    try:
                        parsed = int(score_val)
                    except (ValueError, TypeError):
                        parsed = None
                else:
                    parsed = None
                if name == event.get("home_team"):
                    home_score = parsed
                elif name == event.get("away_team"):
                    away_score = parsed

        result.append(MatchScore(
            event_id=event.get("id", ""),
            home_team=event.get("home_team", ""),
            away_team=event.get("away_team", ""),
            home_score=home_score,
            away_score=away_score,
            period="",  # Odds API scores endpoint doesn't provide period
            is_completed=event.get("completed", False),
            last_updated=event.get("last_update") or "",
        ))
    return result


def fetch_scores(client: OddsAPIClient, sport_key: str) -> list[MatchScore]:
    """Belirtilen spor için canlı skorları çek.

    Returns:
        MatchScore listesi. API hatası → boş liste.
    """
    raw = client.get_scores(sport_key)
    if raw is None:
        return []
    return _parse_scores(raw)
