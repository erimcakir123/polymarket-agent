"""Bookmaker probability engine (TDD §6.1) — pure, no I/O."""
from __future__ import annotations

from dataclasses import dataclass

from src.domain.analysis.confidence import derive_confidence


@dataclass
class BookmakerProbability:
    probability: float       # Son olasılık [0.05, 0.95]
    confidence: str          # "A" / "B" / "C"
    num_bookmakers: float    # Toplam bookmaker ağırlığı
    has_sharp: bool          # Pinnacle / Betfair Exchange var mı
    bookmaker_prob: float = 0.0    # Ham bookmaker olasılığı (default: 0.0)


def calculate_bookmaker_probability(
    bookmaker_prob: float | None = None,
    num_bookmakers: float = 0,
    has_sharp: bool = False,
) -> BookmakerProbability:
    """Bookmaker verisinden P(YES) hesapla. Yetersiz veride 0.5 döner (C conf)."""
    confidence = derive_confidence(num_bookmakers, has_sharp)

    if bookmaker_prob is None or bookmaker_prob <= 0 or num_bookmakers < 1:
        return BookmakerProbability(
            probability=0.5,
            confidence=confidence,
            num_bookmakers=num_bookmakers,
            has_sharp=has_sharp,
            bookmaker_prob=0.0,
        )

    clamped = max(0.05, min(0.95, bookmaker_prob))
    return BookmakerProbability(
        probability=round(clamped, 4),
        confidence=confidence,
        num_bookmakers=num_bookmakers,
        has_sharp=has_sharp,
        bookmaker_prob=round(bookmaker_prob, 4),
    )
