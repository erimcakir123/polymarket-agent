"""MLB Submarket Engine Protocol (SPEC-R Plan 1 — interface only).

Gerçek implementation Plan 2+3+4'te `src/strategy/entry/mlb_submarket_engine.py`
dosyasında yapılacak. Bu Protocol sayesinde scanner Plan 1'de mock engine ile
test edilebilir, gerçek engine eklendiğinde signature uyumu garanti.
"""
from __future__ import annotations

from typing import Protocol

from src.models.market import MarketData
from src.models.signal import Signal


class MlbSubmarketEngineProtocol(Protocol):
    """MLB totals/run-line için model-anchor signal üretici."""

    def process(self, market: MarketData) -> Signal | None:
        """Bir market'i değerlendirir.

        Returns:
            Signal: edge ≥ min_edge ise.
            None: edge yok, lineup belirsiz, veri eksik, vs.
        """
        ...
