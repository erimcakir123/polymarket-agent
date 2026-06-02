"""ACB scraper: HTML parser test (mock fixture)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.infrastructure.data.basketball.acb_scraper import (
    AcbScraper,
    _name_to_abbr,
    _parse_spanish_date,
    _parse_one_game,
)
from src.infrastructure.data.basketball.data_source_health import HealthTracker


# Mock HTML — gercek site yapisina yakin minimum fixture.
_FIXTURE_HTML = """
<html><body>
<div class="partido">
  <a class="equipo" href="/equipo/1">Real Madrid</a>
  <span class="resultado">85 - 78</span>
  <a class="equipo" href="/equipo/2">La Laguna Tenerife</a>
  <span class="fecha">2 de junio de 2026</span>
</div>
<div class="partido">
  <a class="equipo" href="/equipo/3">Valencia</a>
  <span class="resultado">92 - 88</span>
  <a class="equipo" href="/equipo/4">Bilbao Basket</a>
  <span class="fecha">3 de junio de 2026</span>
</div>
</body></html>
"""


def test_name_to_abbr_known() -> None:
    assert _name_to_abbr("Real Madrid") == "RM"
    assert _name_to_abbr("real madrid") == "RM"
    assert _name_to_abbr("FC Barcelona") == "FCB"
    assert _name_to_abbr("Bilbao Basket") == "BIL"
    assert _name_to_abbr("La Laguna Tenerife") == "LAL"


def test_name_to_abbr_unknown_returns_none() -> None:
    assert _name_to_abbr("Unknown Team XYZ") is None
    assert _name_to_abbr("") is None


def test_parse_spanish_date_with_year() -> None:
    dt = _parse_spanish_date("4 de octubre de 2025", default_year=2026)
    assert dt is not None
    assert dt.year == 2025 and dt.month == 10 and dt.day == 4


def test_parse_spanish_date_without_year_uses_default() -> None:
    dt = _parse_spanish_date("15 de marzo", default_year=2026)
    assert dt is not None
    assert dt.year == 2026 and dt.month == 3 and dt.day == 15


def test_parse_spanish_date_invalid_returns_none() -> None:
    assert _parse_spanish_date("invalid date string", default_year=2026) is None
    assert _parse_spanish_date("32 de enero de 2026", default_year=2026) is None


def test_scraper_parses_fixture_html(tmp_path: Path) -> None:
    health = HealthTracker(tmp_path / "h.json")
    sc = AcbScraper(
        health=health,
        http_get=lambda url: _FIXTURE_HTML,
        sleep_fn=lambda s: None,
    )
    result = sc.refresh("2025-26")
    assert result.ok is True
    assert result.source == "acb_scraper"
    assert len(result.games) == 2
    g = result.games[0]
    assert g.home_team == "RM"
    assert g.away_team == "LAL"
    assert g.home_score == 85
    assert g.away_score == 78
    assert g.date_utc.year == 2026 and g.date_utc.month == 6 and g.date_utc.day == 2


def test_scraper_teams_extracted(tmp_path: Path) -> None:
    health = HealthTracker(tmp_path / "h.json")
    sc = AcbScraper(
        health=health,
        http_get=lambda url: _FIXTURE_HTML,
        sleep_fn=lambda s: None,
    )
    result = sc.refresh("2025-26")
    assert "RM" in result.teams
    assert "LAL" in result.teams
    assert "VAL" in result.teams
    assert "BIL" in result.teams


def test_scraper_empty_html_triggers_zero_parsed_data_fail(tmp_path: Path) -> None:
    """ZERO_PARSED_DATA koruması (2026-06-03): bos HTML → teams=[]+games=[] → fail.

    Eski davranis "silent skip" tehlikeli — React-rendered sayfa veya CSS
    selector degisimi yutulurdu. Yeni davranis: base_scraper.refresh()
    "hem teams hem games bos → fail" yapar.
    """
    health = HealthTracker(tmp_path / "h.json")
    sc = AcbScraper(
        health=health,
        http_get=lambda url: "<html><body></body></html>",
        sleep_fn=lambda s: None,
    )
    result = sc.refresh("2025-26")
    assert result.ok is False
    assert "ZERO_PARSED_DATA" in (result.error or "")


def test_scraper_malformed_row_silently_skipped(tmp_path: Path) -> None:
    """Tek bozuk row (eksik takim) → o row skip, kalan games OK."""
    bad_html = """
    <html><body>
      <div class="partido"><span class="resultado">XX - YY</span></div>
      <div class="partido">
        <a class="equipo">Real Madrid</a>
        <span class="resultado">85 - 78</span>
        <a class="equipo">Valencia</a>
        <span class="fecha">1 de junio de 2026</span>
      </div>
    </body></html>
    """
    health = HealthTracker(tmp_path / "h.json")
    sc = AcbScraper(
        health=health,
        http_get=lambda url: bad_html,
        sleep_fn=lambda s: None,
    )
    result = sc.refresh("2025-26")
    assert result.ok is True
    assert len(result.games) == 1
    assert result.games[0].home_team == "RM"
