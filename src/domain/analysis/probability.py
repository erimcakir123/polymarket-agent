"""Bookmaker probability engine (DECISIONS §6.1) — pure, no I/O."""
from __future__ import annotations

from dataclasses import dataclass

from src.domain.analysis.confidence import derive_confidence


@dataclass
class BookmakerProbability:
    probability: float       # Son olasılık [0.05, 0.95]
    confidence: str          # "A" / "B" / "C"
    bookmaker_prob: float    # Ham olasılık (bookmaker veya model — source alanı belirtir)
    num_bookmakers: float    # Toplam ağırlık (model için sharp-equivalent eşdeğer)
    has_sharp: bool          # Pinnacle / Betfair Exchange var mı (model için True default)
    # K4 (2026-05-31): tennis modeli BookmakerProbability tipini paylaşıyor; alan
    # adı kalır (blast radius), source ayrımı dashboard/audit için eklendi.
    source: str = "bookmaker"  # "bookmaker" | "model"


def calculate_bookmaker_probability(
    bookmaker_prob: float | None = None,
    num_bookmakers: float = 0,
    has_sharp: bool = False,
    source: str = "bookmaker",
) -> BookmakerProbability:
    """Probability sinyali — bookmaker veya model verisinden P(YES). Yetersiz veride 0.5 (C)."""
    confidence = derive_confidence(num_bookmakers, has_sharp)

    if bookmaker_prob is None or bookmaker_prob <= 0 or num_bookmakers < 1:
        return BookmakerProbability(
            probability=0.5,
            confidence=confidence,
            bookmaker_prob=0.0,
            num_bookmakers=num_bookmakers,
            has_sharp=has_sharp,
            source=source,
        )

    clamped = max(0.05, min(0.95, bookmaker_prob))
    return BookmakerProbability(
        probability=round(clamped, 4),
        confidence=confidence,
        bookmaker_prob=round(bookmaker_prob, 4),
        num_bookmakers=num_bookmakers,
        has_sharp=has_sharp,
        source=source,
    )
