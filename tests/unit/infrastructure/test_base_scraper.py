"""EuropeanBasketScraper base class testleri (retry, parse fail, health update)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import requests

from src.infrastructure.data.basketball.base_scraper import (
    EuropeanBasketScraper,
    ScrapedGame,
)
from src.infrastructure.data.basketball.data_source_health import HealthTracker


class _StubScraper(EuropeanBasketScraper):
    SOURCE = "acb_scraper"
    RETRY_BACKOFF_SEC = 0  # test'lerde bekleme yok

    def __init__(self, *, fetch=None, parse_teams=None, parse_games=None, **kw):
        super().__init__(**kw)
        self._fetch = fetch or (lambda season: "<html/>")
        self._pteams = parse_teams or (lambda html: ["RM", "FCB"])
        self._pgames = parse_games or (lambda html: [])

    def _fetch_html(self, season):
        return self._fetch(season)

    def _parse_teams(self, html):
        return self._pteams(html)

    def _parse_games(self, html):
        return self._pgames(html)


def _health(tmp_path: Path) -> HealthTracker:
    return HealthTracker(tmp_path / "health.json")


def test_refresh_success_records_health(tmp_path: Path) -> None:
    health = _health(tmp_path)
    games = [ScrapedGame(
        date_utc=datetime(2026, 6, 1, tzinfo=timezone.utc),
        home_team="RM", away_team="FCB",
        home_score=80, away_score=75,
    )]
    sc = _StubScraper(
        health=health,
        parse_games=lambda html: games,
        sleep_fn=lambda s: None,
    )
    result = sc.refresh("2025-26")
    assert result.ok is True
    assert result.source == "acb_scraper"
    assert len(result.games) == 1
    assert health.consecutive_fails("acb_scraper") == 0
    assert health.is_active("acb_scraper") is True


def test_refresh_http_fail_retries_then_records_failure(tmp_path: Path) -> None:
    health = _health(tmp_path)
    attempts = []

    def boom(season):
        attempts.append(season)
        raise requests.ConnectionError("ban")

    sc = _StubScraper(health=health, fetch=boom, sleep_fn=lambda s: None)
    result = sc.refresh("2025-26")
    assert result.ok is False
    assert "ConnectionError" in (result.error or "")
    assert len(attempts) == 3  # RETRY_COUNT
    assert health.consecutive_fails("acb_scraper") == 1


def test_refresh_parse_fail_no_retry(tmp_path: Path) -> None:
    """Parse hatasi sistematik — retry yardim etmez, hemen fail."""
    health = _health(tmp_path)
    attempts = []

    def bad_parse(html):
        attempts.append(html)
        raise KeyError("missing column")

    sc = _StubScraper(
        health=health, parse_games=bad_parse, sleep_fn=lambda s: None,
    )
    result = sc.refresh("2025-26")
    assert result.ok is False
    assert "KeyError" in (result.error or "")
    assert len(attempts) == 1  # retry yok


def test_three_strikes_deactivates_source(tmp_path: Path) -> None:
    """3 ardisik fail -> active=False (HealthTracker mevcut davranisi)."""
    health = _health(tmp_path)
    sc = _StubScraper(
        health=health,
        fetch=lambda s: (_ for _ in ()).throw(requests.ConnectionError("x")),
        sleep_fn=lambda s: None,
    )
    sc.refresh("s")
    sc.refresh("s")
    sc.refresh("s")
    assert health.is_active("acb_scraper") is False


def test_success_after_fail_resets_consecutive(tmp_path: Path) -> None:
    """Ilk refresh tamamen fail, ikinci refresh tamamen success → fails=0."""
    health = _health(tmp_path)
    mode = ["fail"]

    def maybe(season):
        if mode[0] == "fail":
            raise requests.ConnectionError("down")
        return "<html/>"

    sc = _StubScraper(
        health=health, fetch=maybe, sleep_fn=lambda s: None,
    )
    sc.refresh("s")  # 3 attempt hepsi fail
    assert health.consecutive_fails("acb_scraper") == 1
    mode[0] = "ok"
    sc.refresh("s")  # ilk attempt success
    assert health.consecutive_fails("acb_scraper") == 0
    assert health.is_active("acb_scraper") is True
