"""Avrupa basket lig scraper'lari icin abstract base (SPEC-EUROBASKET-001).

NO_DATA_NO_TRADE: scraper fail -> cache fallback (mevcut TeamRatingsStore JSON
zaten persisted, 48h+ eski ise reject) -> ratings bos donerse basketball_dispatch
o ligi reddeder, trade YAPILMAZ.

Lig-spesifik subclass override eder: _fetch_html, _parse_teams, _parse_games.
Common: retry/backoff/HealthTracker entegrasyonu (mevcut 3-strike fallback API).
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone

import requests

from src.infrastructure.data.basketball.data_source_health import HealthTracker

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScrapedGame:
    """Tek bir tamamlanmis Avrupa basket maci (HTML'den parse edilmis)."""
    date_utc: datetime
    home_team: str    # standart kisaltma (resolver ile uyumlu)
    away_team: str
    home_score: int
    away_score: int


@dataclass(frozen=True)
class ScrapeResult:
    """Refresh sonucu — caller bunu Glicko/TeamSnapshot pipeline'a verir."""
    source: str       # "acb_scraper" / "bsl_scraper" / "lega_scraper" / "vtb_scraper"
    games: tuple[ScrapedGame, ...]
    teams: tuple[str, ...]
    ok: bool
    error: str | None = None


class EuropeanBasketScraper(ABC):
    """Lig-spesifik scraper base class.

    Subclass override: SOURCE (str literal), _fetch_html, _parse_teams, _parse_games.
    Common davranis: User-Agent + timeout + retry + HealthTracker update.

    Hata yonetimi (ARCH_GUARD §12):
    - Infrastructure: try/except + anlamli log + HealthTracker fail kaydi
    - Parse hatasi (ValueError/KeyError) -> ok=False + error mesaji
    - HTTP hatasi -> retry (3 deneme) -> tum retry fail -> ok=False
    """

    SOURCE: str                            # subclass set eder: "acb_scraper" vb.
    REQUEST_TIMEOUT_SEC: int = 15
    RETRY_COUNT: int = 3
    RETRY_BACKOFF_SEC: int = 5
    USER_AGENT: str = "Polymarket-Agent/2.0 (basketball-research)"

    def __init__(
        self,
        health: HealthTracker,
        http_get=None,
        now_fn=lambda: datetime.now(timezone.utc),
        sleep_fn=time.sleep,
    ) -> None:
        self._health = health
        self._http_get = http_get or self._default_http_get
        self._now = now_fn
        self._sleep = sleep_fn

    # ── Subclass contract ──

    @abstractmethod
    def _fetch_html(self, season: str) -> str:
        """Lig sitesinden HTML cek. _http_get helper kullan."""

    @abstractmethod
    def _parse_teams(self, html: str) -> list[str]:
        """HTML'den takim listesi (standart kisaltma)."""

    @abstractmethod
    def _parse_games(self, html: str) -> list[ScrapedGame]:
        """HTML'den tamamlanmis mac sonuclari."""

    # ── Public entry point ──

    def refresh(self, season: str) -> ScrapeResult:
        """Retry + HealthTracker update + parse → ScrapeResult."""
        now_iso = self._now().isoformat()
        last_err: str | None = None
        for attempt in range(self.RETRY_COUNT):
            try:
                html = self._fetch_html(season)
                teams = self._parse_teams(html)
                games = self._parse_games(html)
                self._health.record_success(self.SOURCE, at_utc=now_iso)
                return ScrapeResult(
                    source=self.SOURCE,
                    games=tuple(games),
                    teams=tuple(teams),
                    ok=True,
                )
            except requests.RequestException as e:
                last_err = f"HTTP {type(e).__name__}: {e}"
                logger.warning(
                    "%s fetch fail (attempt %d/%d): %s",
                    self.SOURCE, attempt + 1, self.RETRY_COUNT, last_err,
                )
                if attempt < self.RETRY_COUNT - 1:
                    self._sleep(self.RETRY_BACKOFF_SEC * (2 ** attempt))
                    continue
            except (ValueError, KeyError, IndexError, AttributeError) as e:
                # Parse hatasi - retry yardim etmez, hemen fail
                last_err = f"parse {type(e).__name__}: {e}"
                logger.error("%s parse fail: %s", self.SOURCE, last_err)
                break
        self._health.record_failure(self.SOURCE, at_utc=now_iso)
        return ScrapeResult(
            source=self.SOURCE, games=(), teams=(), ok=False, error=last_err,
        )

    # ── Helpers ──

    def _default_http_get(self, url: str) -> str:
        resp = requests.get(
            url,
            headers={"User-Agent": self.USER_AGENT},
            timeout=self.REQUEST_TIMEOUT_SEC,
        )
        resp.raise_for_status()
        return resp.text
