"""LAB v2: Sharp-book (Pinnacle / Betfair Ex / Smarkets) priority filter.

Mevcut sistem sharp book'lara 3x weight veriyor ama YINE ortalamayi kullaniyor.
Lab v2'de hipotez: SADECE sharp book'larin fiyatini referans al → Pinnacle yoksa
weighted ortalama fallback.

Wrap odds_enricher.enrich_market — sharp_only mode aktif.

Main bot UNTOUCHED.
"""
from __future__ import annotations

from typing import Callable

from src.domain.analysis.enrich_outcome import EnrichResult
from src.domain.matching.bookmaker_weights import is_sharp
from src.models.market import MarketData


def make_pinnacle_first_enricher(
    base_enricher: Callable[[MarketData], EnrichResult],
    raw_bookmaker_reader: Callable[[MarketData], list[dict]] | None = None,
) -> Callable[[MarketData], EnrichResult]:
    """Wrap odds_enricher: sharp varsa SADECE sharp'in fiyatini kullan.

    raw_bookmaker_reader (optional): returns list of dicts like
      [{"name": "Pinnacle", "yes_prob": 0.62}, ...]
    Yoksa: base_enricher cagrilir (degisiklik yok — geri uyumlu fallback).
    """
    def enrich(market: MarketData) -> EnrichResult:
        if raw_bookmaker_reader is None:
            return base_enricher(market)
        try:
            books = raw_bookmaker_reader(market)
        except Exception:  # noqa: BLE001 — lab safety
            return base_enricher(market)
        sharp_probs = [b["yes_prob"] for b in books if is_sharp(b.get("name", ""))]
        if not sharp_probs:
            return base_enricher(market)
        # Sharp-only ortalama (genelde 1 Pinnacle olur)
        from src.domain.analysis.probability import calculate_bookmaker_probability
        avg = sum(sharp_probs) / len(sharp_probs)
        return EnrichResult(
            probability=calculate_bookmaker_probability(
                bookmaker_prob=avg,
                num_bookmakers=float(len(sharp_probs)),
                has_sharp=True,
                source="pinnacle_sharp_only",
            ),
            fail_reason=None,
        )

    return enrich
