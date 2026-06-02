"""Turkiye BSL scraper — PLACEHOLDER (live HTML parser TODO).

Sezon basinda gercek tbf.org.tr veya tblstat.com HTML parser eklenecek.
Su an: _fetch_html NotImplementedError firlatir → base scraper parse fail
yakalar → HealthTracker fail → 3-strike sonra "broken" → telegram alert.

NO_DATA_NO_TRADE devrede: ratings bos kalir, basketball_dispatch BSL slug'i
reddeder, trade YAPILMAZ. Pattern: AcbScraper'a bak (referans implementasyon).
"""
from __future__ import annotations

from src.infrastructure.data.basketball.base_scraper import (
    EuropeanBasketScraper,
    ScrapedGame,
)


class BslScraper(EuropeanBasketScraper):
    SOURCE = "bsl_scraper"

    def _fetch_html(self, season: str) -> str:
        raise NotImplementedError(
            f"BSL HTML parser implemente edilmemis (season={season}). "
            "Implementasyon icin AcbScraper'a bak."
        )

    def _parse_teams(self, html: str) -> list[str]:
        return []

    def _parse_games(self, html: str) -> list[ScrapedGame]:
        return []
