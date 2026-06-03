"""Lega Basket Serie A scraper: HTML parser test (mock fixture).

Kaynak: eurobasket.com Italy sayfasi (legabasket.it 404 + React-rendered;
eurobasket VTB ile birebir GamesDate/GamesTeam/GamesResult patterni).
"""
from __future__ import annotations

from pathlib import Path

from src.infrastructure.data.basketball.data_source_health import HealthTracker
from src.infrastructure.data.basketball.lega_scraper import (
    LegaScraper,
    _name_to_abbr,
    _parse_english_short_date,
    _parse_italian_date,
)


# Mock HTML — eurobasket Italy gercek yapisindan (245+ row arasindan 2 ornek):
# kisaltilmis takim isimleri ("Virtus BO", "Reggio Em."), "Jun.1:" tarih format.
_FIXTURE_HTML = """
<html><body>
<table>
<tr class="gamesschedulegames-1-1">
<td class="GamesDate">Jun.1:</td>
<td class="GamesTeam TextAlignRight"><b>Virtus BO</b></td>
<td class="GamesResult TextAlignCenter"><a>&nbsp;98-79&nbsp;</a></td>
<td class="GamesTeam TextAlignLeft">Venezia</td>
<td class="MediaGuide"></td>
</tr>
<tr class="gamesschedulegames-1-1">
<td class="GamesDate">May 31:</td>
<td class="GamesTeam TextAlignRight"><b>Brescia</b></td>
<td class="GamesResult TextAlignCenter"><a>&nbsp;85-79&nbsp;</a></td>
<td class="GamesTeam TextAlignLeft">Milano</td>
<td class="MediaGuide"></td>
</tr>
<tr class="gamesschedulegames-1-1">
<td class="GamesDate">May 28:</td>
<td class="GamesTeam TextAlignRight"><b>Reggio Em.</b></td>
<td class="GamesResult TextAlignCenter"><a>&nbsp;72-68&nbsp;</a></td>
<td class="GamesTeam TextAlignLeft">Sassari</td>
<td class="MediaGuide"></td>
</tr>
</table>
</body></html>
"""


def test_name_to_abbr_known() -> None:
    # Eurobasket kisa formlari
    assert _name_to_abbr("Milano") == "MILA"
    assert _name_to_abbr("Virtus BO") == "VIRT"
    assert _name_to_abbr("Venezia") == "REY"
    assert _name_to_abbr("Reggio Em.") == "REG"  # trailing dot normalize
    assert _name_to_abbr("Sassari") == "SASS"
    # Uzun sponsor formlari
    assert _name_to_abbr("Olimpia Milano") == "MILA"
    assert _name_to_abbr("Virtus Bologna") == "VIRT"
    assert _name_to_abbr("Pallacanestro Trieste") == "TRI"


def test_name_to_abbr_unknown_returns_none() -> None:
    assert _name_to_abbr("Unknown Squadra XYZ") is None
    assert _name_to_abbr("") is None


def test_parse_english_short_date_with_dot() -> None:
    dt = _parse_english_short_date("Jun.1:", default_year=2026)
    assert dt is not None
    assert dt.year == 2026 and dt.month == 6 and dt.day == 1


def test_parse_english_short_date_with_space() -> None:
    dt = _parse_english_short_date("May 28:", default_year=2026)
    assert dt is not None
    assert dt.year == 2026 and dt.month == 5 and dt.day == 28


def test_parse_english_short_date_invalid_returns_none() -> None:
    assert _parse_english_short_date("not a date", default_year=2026) is None


# ── Legacy Italian-date helper (eski legabasket.it fixture'lari icin korundu) ──


def test_parse_italian_date_with_year() -> None:
    dt = _parse_italian_date("12 giugno 2026", default_year=2025)
    assert dt is not None
    assert dt.year == 2026 and dt.month == 6 and dt.day == 12


def test_parse_italian_date_without_year_uses_default() -> None:
    dt = _parse_italian_date("15 marzo", default_year=2026)
    assert dt is not None
    assert dt.year == 2026 and dt.month == 3 and dt.day == 15


def test_parse_italian_date_all_months() -> None:
    """12 ay tablosu — yazim hatalari erken yakalansin."""
    months = [
        ("gennaio", 1), ("febbraio", 2), ("marzo", 3), ("aprile", 4),
        ("maggio", 5), ("giugno", 6), ("luglio", 7), ("agosto", 8),
        ("settembre", 9), ("ottobre", 10), ("novembre", 11), ("dicembre", 12),
    ]
    for name, expected_month in months:
        dt = _parse_italian_date(f"1 {name} 2026", default_year=2026)
        assert dt is not None, f"{name} parse fail"
        assert dt.month == expected_month, (
            f"{name} → ay {dt.month}, beklenen {expected_month}"
        )


def test_parse_italian_date_invalid_returns_none() -> None:
    assert _parse_italian_date("data non valida", default_year=2026) is None
    # 32 giugno → ValueError → None (sessiz skip)
    assert _parse_italian_date("32 giugno 2026", default_year=2026) is None


# ── Scraper end-to-end (eurobasket fixture) ──


def test_scraper_parses_fixture_html(tmp_path: Path) -> None:
    health = HealthTracker(tmp_path / "h.json")
    sc = LegaScraper(
        health=health,
        http_get=lambda url: _FIXTURE_HTML,
        sleep_fn=lambda s: None,
    )
    result = sc.refresh("2025-26")
    assert result.ok is True
    assert result.source == "lega_scraper"
    assert len(result.games) == 3
    g = result.games[0]
    assert g.home_team == "VIRT"
    assert g.away_team == "REY"
    assert g.home_score == 98
    assert g.away_score == 79
    assert g.date_utc.month == 6 and g.date_utc.day == 1


def test_scraper_teams_extracted(tmp_path: Path) -> None:
    health = HealthTracker(tmp_path / "h.json")
    sc = LegaScraper(
        health=health,
        http_get=lambda url: _FIXTURE_HTML,
        sleep_fn=lambda s: None,
    )
    result = sc.refresh("2025-26")
    # Fixture'da 3 mac → 6 takim slot ama 5 unique (Virtus/Venezia/Brescia/
    # Milano/Reggio/Sassari = 6 unique aslinda)
    assert "VIRT" in result.teams
    assert "REY" in result.teams
    assert "BRE" in result.teams
    assert "MILA" in result.teams
    assert "REG" in result.teams
    assert "SASS" in result.teams


def test_scraper_empty_html_triggers_zero_parsed_data_fail(tmp_path: Path) -> None:
    """ZERO_PARSED_DATA (2026-06-03): bos HTML → fail.

    Eski legabasket.it React-rendered yutmasini engelleyen koruma;
    eurobasket icin de geçerli (CSS class degisirse parser kor olur).
    """
    health = HealthTracker(tmp_path / "h.json")
    sc = LegaScraper(
        health=health,
        http_get=lambda url: "<html><body></body></html>",
        sleep_fn=lambda s: None,
    )
    result = sc.refresh("2025-26")
    assert result.ok is False
    assert "ZERO_PARSED_DATA" in (result.error or "")


def test_scraper_malformed_row_silently_skipped(tmp_path: Path) -> None:
    """Tek bozuk row (eksik takim hucresi) → o row skip, kalan games OK."""
    bad_html = """
    <html><body>
    <table>
      <tr>
        <td class="GamesDate">Jun.1:</td>
        <td class="GamesResult"><a>XX-YY</a></td>
      </tr>
      <tr>
        <td class="GamesDate">Jun.2:</td>
        <td class="GamesTeam TextAlignRight"><b>Milano</b></td>
        <td class="GamesResult"><a>85-78</a></td>
        <td class="GamesTeam TextAlignLeft">Virtus BO</td>
      </tr>
    </table>
    </body></html>
    """
    health = HealthTracker(tmp_path / "h.json")
    sc = LegaScraper(
        health=health,
        http_get=lambda url: bad_html,
        sleep_fn=lambda s: None,
    )
    result = sc.refresh("2025-26")
    assert result.ok is True
    assert len(result.games) == 1
    assert result.games[0].home_team == "MILA"
    assert result.games[0].away_team == "VIRT"
