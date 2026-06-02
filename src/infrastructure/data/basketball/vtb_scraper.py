"""Rusya VTB United League scraper — PLACEHOLDER (live HTML parser TODO).

Implementasyon: vtb-league.com calendar sayfasi. AcbScraper pattern paralel.
NO_DATA_NO_TRADE devrede: bos ratings → trade YOK.
"""
from __future__ import annotations

from src.infrastructure.data.basketball.base_scraper import (
    EuropeanBasketScraper,
    ScrapedGame,
)


class VtbScraper(EuropeanBasketScraper):
    SOURCE = "vtb_scraper"

    def _fetch_html(self, season: str) -> str:
        raise NotImplementedError(
            f"VTB HTML parser implemente edilmemis (season={season}). "
            "Implementasyon icin AcbScraper'a bak."
        )

    def _parse_teams(self, html: str) -> list[str]:
        return []

    def _parse_games(self, html: str) -> list[ScrapedGame]:
        return []
