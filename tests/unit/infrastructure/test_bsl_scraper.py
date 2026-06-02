"""BSL scraper: HTML parser test (mock fixture)."""
from __future__ import annotations

from pathlib import Path

from src.infrastructure.data.basketball.bsl_scraper import (
    BslScraper,
    _name_to_abbr,
    _parse_turkish_date,
)
from src.infrastructure.data.basketball.data_source_health import HealthTracker


# Mock HTML — eurobasket.com flat-div results pattern + ek alternatif row.
_FIXTURE_HTML = """
<html><body>
<div>
  12 Haziran 2026:
  <a href="/Turkey/Team/Besiktas">Besiktas</a>
  [82-79]
  <a href="/Turkey/Team/Bahcesehir">Bahcese.</a>
</div>
<div>
  3 Haziran 2026:
  <a href="/Turkey/Team/Fenerbahce">Fenerba.</a>
  [88-85]
  <a href="/Turkey/Team/Anadolu">Anadolu E</a>
</div>
</body></html>
"""


def test_name_to_abbr_known_full_names() -> None:
    assert _name_to_abbr("Besiktas") == "BES"
    assert _name_to_abbr("Fenerbahce") == "FEN"
    assert _name_to_abbr("Anadolu Efes") == "ANA"
    assert _name_to_abbr("Galatasaray") == "GAL"


def test_name_to_abbr_known_eurobasket_abbreviated() -> None:
    """Eurobasket "Bahcese.", "Fenerba.", "Anadolu E" gibi kisa formlar."""
    assert _name_to_abbr("Bahcese") == "BAH"
    assert _name_to_abbr("Fenerba") == "FEN"
    assert _name_to_abbr("Anadolu E") == "ANA"


def test_name_to_abbr_unknown_returns_none() -> None:
    assert _name_to_abbr("Unknown Team XYZ") is None
    assert _name_to_abbr("") is None


def test_parse_turkish_date_with_year() -> None:
    dt = _parse_turkish_date("12 Haziran 2026", default_year=2025)
    assert dt is not None
    assert dt.year == 2026 and dt.month == 6 and dt.day == 12


def test_parse_turkish_date_without_year_uses_default() -> None:
    dt = _parse_turkish_date("3 Aralık", default_year=2026)
    assert dt is not None
    assert dt.year == 2026 and dt.month == 12 and dt.day == 3


def test_parse_turkish_date_ascii_fallback() -> None:
    """Turkce karakter yoksa (subat/mayis/agustos) yine parse etmeli."""
    dt = _parse_turkish_date("15 Mayis 2026", default_year=2026)
    assert dt is not None
    assert dt.month == 5 and dt.day == 15


def test_parse_turkish_date_english_short_fallback() -> None:
    """Eurobasket bazen 'Jun.2' / 'May 16' Ingilizce kisa kullaniyor."""
    dt = _parse_turkish_date("Jun.2 2026", default_year=2026)
    assert dt is not None
    assert dt.month == 6 and dt.day == 2


def test_parse_turkish_date_invalid_returns_none() -> None:
    assert _parse_turkish_date("invalid date string", default_year=2026) is None
    assert _parse_turkish_date("32 Ocak 2026", default_year=2026) is None


def test_scraper_parses_fixture_html(tmp_path: Path) -> None:
    health = HealthTracker(tmp_path / "h.json")
    sc = BslScraper(
        health=health,
        http_get=lambda url: _FIXTURE_HTML,
        sleep_fn=lambda s: None,
    )
    result = sc.refresh("2025-26")
    assert result.ok is True
    assert result.source == "bsl_scraper"
    assert len(result.games) == 2
    g = result.games[0]
    assert g.home_team == "BES"
    assert g.away_team == "BAH"
    assert g.home_score == 82
    assert g.away_score == 79
    assert g.date_utc.year == 2026 and g.date_utc.month == 6 and g.date_utc.day == 12


def test_scraper_teams_extracted(tmp_path: Path) -> None:
    health = HealthTracker(tmp_path / "h.json")
    sc = BslScraper(
        health=health,
        http_get=lambda url: _FIXTURE_HTML,
        sleep_fn=lambda s: None,
    )
    result = sc.refresh("2025-26")
    assert "BES" in result.teams
    assert "BAH" in result.teams
    assert "FEN" in result.teams
    assert "ANA" in result.teams


def test_scraper_empty_html_triggers_zero_parsed_data_fail(tmp_path: Path) -> None:
    """ZERO_PARSED_DATA (2026-06-03): bos HTML → fail (silent skip kaldirildi)."""
    health = HealthTracker(tmp_path / "h.json")
    sc = BslScraper(
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
      <div>NoTeam [XX-YY]</div>
      <div>
        12 Haziran 2026:
        <a href="/x">Besiktas</a>
        [82-79]
        <a href="/y">Bahcesehir</a>
      </div>
    </body></html>
    """
    health = HealthTracker(tmp_path / "h.json")
    sc = BslScraper(
        health=health,
        http_get=lambda url: bad_html,
        sleep_fn=lambda s: None,
    )
    result = sc.refresh("2025-26")
    assert result.ok is True
    assert len(result.games) == 1
    assert result.games[0].home_team == "BES"
