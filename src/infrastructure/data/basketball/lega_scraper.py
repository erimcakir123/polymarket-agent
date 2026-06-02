"""Italya Lega Serie A scraper — PLACEHOLDER (live HTML parser TODO).

Implementasyon: legabasket.it calendario sayfasi. AcbScraper pattern paralel.
NO_DATA_NO_TRADE devrede: bos ratings → trade YOK.
"""
from __future__ import annotations

from src.infrastructure.data.basketball.base_scraper import (
    EuropeanBasketScraper,
    ScrapedGame,
)


class LegaScraper(EuropeanBasketScraper):
    SOURCE = "lega_scraper"

    def _fetch_html(self, season: str) -> str:
        raise NotImplementedError(
            f"Lega HTML parser implemente edilmemis (season={season}). "
            "Implementasyon icin AcbScraper'a bak."
        )

    def _parse_teams(self, html: str) -> list[str]:
        return []

    def _parse_games(self, html: str) -> list[ScrapedGame]:
        return []
