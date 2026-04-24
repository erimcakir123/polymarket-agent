"""Bookmaker probability engine (TDD §6.1) — pure, no I/O."""
from __future__ import annotations

from dataclasses import dataclass

from src.domain.analysis.confidence import derive_confidence


@dataclass
class BookmakerProbability:
    probability: float       # Son olasılık [0.05, 0.95]
    confidence: str          # "A" / "B" / "C"
    bookmaker_prob: float    # Ham bookmaker olasılığı
    num_bookmakers: float    # Toplam bookmaker ağırlığı (weighted)
    has_sharp: bool          # Pinnacle / Betfair Exchange var mı
    # PLAN-013: gerçek sayılar (ağırlık değil) — entry gate kalite filtresi
    num_bookmakers_count: int = 0    # Gerçek bookmaker sayısı
    num_sharps: int = 0              # Sharp bookmaker sayısı


def calculate_bookmaker_probability(
    bookmaker_prob: float | None = None,
    num_bookmakers: float = 0,
    has_sharp: bool = False,
    num_bookmakers_count: int = 0,
    num_sharps: int = 0,
) -> BookmakerProbability:
    """Bookmaker verisinden P(YES) hesapla. Yetersiz veride 0.5 döner (C conf)."""
    confidence = derive_confidence(num_bookmakers, has_sharp)

    if bookmaker_prob is None or bookmaker_prob <= 0 or num_bookmakers < 1:
        return BookmakerProbability(
            probability=0.5,
            confidence=confidence,
            bookmaker_prob=0.0,
            num_bookmakers=num_bookmakers,
            has_sharp=has_sharp,
            num_bookmakers_count=num_bookmakers_count,
            num_sharps=num_sharps,
        )

    clamped = max(0.05, min(0.95, bookmaker_prob))
    return BookmakerProbability(
        probability=round(clamped, 4),
        confidence=confidence,
        bookmaker_prob=round(bookmaker_prob, 4),
        num_bookmakers=num_bookmakers,
        has_sharp=has_sharp,
        num_bookmakers_count=num_bookmakers_count,
        num_sharps=num_sharps,
    )
