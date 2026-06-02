"""VTB scraper: eurobasket.com HTML parser test (mock fixture)."""
from __future__ import annotations

from pathlib import Path

from src.infrastructure.data.basketball.data_source_health import HealthTracker
from src.infrastructure.data.basketball.vtb_scraper import (
    VtbScraper,
    _name_to_abbr,
    _parse_english_short_date,
    _parse_one_game,
)


# Mock HTML — eurobasket.com VTB sayfasi gercek yapisindan minimum fixture.
_FIXTURE_HTML = """
<html><body>
<table>
<tr class="gamesschedule">
  <td class="GamesDate">Jun.1:</td>
  <td class="GamesTeam TextAlignRight"><b>Zenit</b></td>
  <td class="GamesResult TextAlignCenter">
    <a href="/box/x.aspx">&nbsp;82-80&nbsp;</a>
  </td>
  <td class="GamesTeam TextAlignLeft">Lokomotiv</td>
  <td class="MediaGuide"></td>
</tr>
<tr class="gamesschedule">
  <td class="GamesDate">Jun.2:</td>
  <td class="GamesTeam TextAlignRight"><b>CSKA</b></td>
  <td class="GamesResult TextAlignCenter">
    <a href="/box/y.aspx">&nbsp;91-63&nbsp;</a>
  </td>
  <td class="GamesTeam TextAlignLeft">UNICS</td>
  <td class="MediaGuide"></td>
</tr>
<tr class="gamesschedule">
  <td class="GamesDate">May 28:</td>
  <td class="GamesTeam TextAlignRight"><b>MBA Mos.</b></td>
  <td class="GamesResult TextAlignCenter">
    <a href="/box/z.aspx">&nbsp;77-72&nbsp;</a>
  </td>
  <td class="GamesTeam TextAlignLeft">Uralmas.</td>
  <td class="MediaGuide"></td>
</tr>
</table>
</body></html>
"""


def test_name_to_abbr_known() -> None:
    assert _name_to_abbr("CSKA") == "CSKA"
    assert _name_to_abbr("Zenit") == "ZEN"
    assert _name_to_abbr("UNICS") == "UNI"
    assert _name_to_abbr("Lokomotiv") == "LOK"
    # Eurobasket noktalı varyantlar
    assert _name_to_abbr("MBA Mos.") == "MBA"
    assert _name_to_abbr("Uralmas.") == "URA"
    assert _name_to_abbr("Lokomoti.") == "LOK"


def test_name_to_abbr_unknown_returns_none() -> None:
    assert _name_to_abbr("Unknown Team XYZ") is None
    assert _name_to_abbr("") is None


def test_name_to_abbr_reserve_team_filtered() -> None:
    """Reserve takım ("-2") ve youth ("Jun.") kabul edilmemeli."""
    assert _name_to_abbr("CSKA-2") is None
    assert _name_to_abbr("CSKA-Jun.") is None
    assert _name_to_abbr("Avtodor-2") is None


def test_parse_english_short_date_with_period() -> None:
    """Eurobasket format: 'Jun.1:' tarih ve nokta ile."""
    dt = _parse_english_short_date("Jun.1:", default_year=2026)
    assert dt is not None
    assert dt.year == 2026 and dt.month == 6 and dt.day == 1


def test_parse_english_short_date_with_space() -> None:
    """Eurobasket format: 'May 28:' boşlukla."""
    dt = _parse_english_short_date("May 28:", default_year=2026)
    assert dt is not None
    assert dt.year == 2026 and dt.month == 5 and dt.day == 28


def test_parse_english_short_date_invalid_returns_none() -> None:
    assert _parse_english_short_date("invalid string", default_year=2026) is None
    assert _parse_english_short_date("Xyz.32:", default_year=2026) is None


def test_scraper_parses_fixture_html(tmp_path: Path) -> None:
    health = HealthTracker(tmp_path / "h.json")
    sc = VtbScraper(
        health=health,
        http_get=lambda url: _FIXTURE_HTML,
        sleep_fn=lambda s: None,
    )
    result = sc.refresh("2025-26")
    assert result.ok is True
    assert result.source == "vtb_scraper"
    assert len(result.games) == 3
    g = result.games[0]
    assert g.home_team == "ZEN"
    assert g.away_team == "LOK"
    assert g.home_score == 82
    assert g.away_score == 80


def test_scraper_teams_extracted(tmp_path: Path) -> None:
    health = HealthTracker(tmp_path / "h.json")
    sc = VtbScraper(
        health=health,
        http_get=lambda url: _FIXTURE_HTML,
        sleep_fn=lambda s: None,
    )
    result = sc.refresh("2025-26")
    assert "CSKA" in result.teams
    assert "ZEN" in result.teams
    assert "UNI" in result.teams
    assert "LOK" in result.teams
    assert "MBA" in result.teams
    assert "URA" in result.teams


def test_scraper_empty_html_triggers_zero_parsed_data_fail(tmp_path: Path) -> None:
    """ZERO_PARSED_DATA (2026-06-03): bos HTML → fail (silent skip kaldirildi)."""
    health = HealthTracker(tmp_path / "h.json")
    sc = VtbScraper(
        health=health,
        http_get=lambda url: "<html><body></body></html>",
        sleep_fn=lambda s: None,
    )
    result = sc.refresh("2025-26")
    assert result.ok is False
    assert "ZERO_PARSED_DATA" in (result.error or "")
