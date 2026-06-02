"""Lega Basket Serie A scraper: HTML parser test (mock fixture)."""
from __future__ import annotations

from pathlib import Path

from src.infrastructure.data.basketball.data_source_health import HealthTracker
from src.infrastructure.data.basketball.lega_scraper import (
    LegaScraper,
    _name_to_abbr,
    _parse_italian_date,
)


# Mock HTML — gercek site yapisina yakin minimum fixture (legabasket.it
# pattern: ".partita" container, ".nome-squadra" team, ".risultato" score,
# ".data-partita" date — AcbScraper pattern paraleli, sadece dil farkli).
_FIXTURE_HTML = """
<html><body>
<div class="partita">
  <a class="nome-squadra" href="/squadre/1">Olimpia Milano</a>
  <span class="risultato">85 - 78</span>
  <a class="nome-squadra" href="/squadre/2">Virtus Bologna</a>
  <span class="data-partita">3 giugno 2026</span>
</div>
<div class="partita">
  <a class="nome-squadra" href="/squadre/3">Reyer Venezia</a>
  <span class="risultato">92 - 88</span>
  <a class="nome-squadra" href="/squadre/4">Dinamo Sassari</a>
  <span class="data-partita">4 giugno 2026</span>
</div>
</body></html>
"""


def test_name_to_abbr_known() -> None:
    assert _name_to_abbr("Olimpia Milano") == "MILA"
    assert _name_to_abbr("olimpia milano") == "MILA"
    assert _name_to_abbr("Virtus Bologna") == "VIRT"
    assert _name_to_abbr("Reyer Venezia") == "REY"
    assert _name_to_abbr("Pallacanestro Trieste") == "TRI"


def test_name_to_abbr_unknown_returns_none() -> None:
    assert _name_to_abbr("Unknown Squadra XYZ") is None
    assert _name_to_abbr("") is None


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
    assert len(result.games) == 2
    g = result.games[0]
    assert g.home_team == "MILA"
    assert g.away_team == "VIRT"
    assert g.home_score == 85
    assert g.away_score == 78
    assert g.date_utc.year == 2026 and g.date_utc.month == 6 and g.date_utc.day == 3


def test_scraper_teams_extracted(tmp_path: Path) -> None:
    health = HealthTracker(tmp_path / "h.json")
    sc = LegaScraper(
        health=health,
        http_get=lambda url: _FIXTURE_HTML,
        sleep_fn=lambda s: None,
    )
    result = sc.refresh("2025-26")
    assert "MILA" in result.teams
    assert "VIRT" in result.teams
    assert "REY" in result.teams
    assert "SASS" in result.teams


def test_scraper_empty_html_no_games(tmp_path: Path) -> None:
    """Bos HTML (sezon disi) → games=[], ok=True (silent skip)."""
    health = HealthTracker(tmp_path / "h.json")
    sc = LegaScraper(
        health=health,
        http_get=lambda url: "<html><body></body></html>",
        sleep_fn=lambda s: None,
    )
    result = sc.refresh("2025-26")
    assert result.ok is True
    assert result.games == ()


def test_scraper_malformed_row_silently_skipped(tmp_path: Path) -> None:
    """Tek bozuk row (eksik takim) → o row skip, kalan games OK."""
    bad_html = """
    <html><body>
      <div class="partita"><span class="risultato">XX - YY</span></div>
      <div class="partita">
        <a class="nome-squadra">Olimpia Milano</a>
        <span class="risultato">85 - 78</span>
        <a class="nome-squadra">Virtus Bologna</a>
        <span class="data-partita">1 giugno 2026</span>
      </div>
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
