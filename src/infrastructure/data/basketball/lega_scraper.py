"""Lega Basket Serie A (Italya) scraper — eurobasket.com Italy sayfa parser.

URL: https://www.eurobasket.com/Italy/basketball-Serie-A.aspx

Eski kaynak (legabasket.it/lba/8/calendario-e-risultati) HTTP 404 + React-rendered;
statik scrape mumkun degil. Eurobasket.com Italy sayfasi VTB ile birebir ayni
HTML pattern'i kullaniyor (GamesDate / GamesTeam / GamesResult <td> hucreleri,
245+ regular season + playoff row, kisaltilmis takim isimleri).

Date format: eurobasket "Jun.1:" / "May 28:" gibi Ingilizce kisaltma.
            Yil yok → sezon takvimine gore default_year ile doldurulur.

Parse stratejisi: BeautifulSoup ile GamesDate/GamesTeam/GamesResult selector,
:has() fallback li. Eslesemezse base scraper ZERO_PARSED_DATA → HealthTracker
fail → NO_DATA_NO_TRADE devreye girer.

NOT: Eurobasket Italy sayfasi LBA-only (Lega Basket Serie A) — Eurolega /
Coppa Italia karismaz. Resolver _LEGA_TEAMS ile hizali 16 takim kisaltmasi:
MILA/VIRT/REY/TRT/SASS/NAP/TRP/DER/CRE/UDI/TRV/CANT/BRE/VAR/REG/TRI.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from src.infrastructure.data.basketball.base_scraper import (
    EuropeanBasketScraper,
    ScrapedGame,
)

logger = logging.getLogger(__name__)


# Takim adi → standart kisaltma (resolver _LEGA_TEAMS ile hizali).
# Eurobasket varyantlari kisaltilmis ("Virtus BO", "Reggio Em.") +
# trailing nokta icerebilir. Polymarket slug abbreviation'lariyla ayni.
_LEGA_NAME_TO_ABBR: dict[str, str] = {
    # Eurobasket short forms
    "milano": "MILA", "virtus bo": "VIRT", "venezia": "REY",
    "trento": "TRT", "sassari": "SASS", "napoli": "NAP",
    "trapani": "TRP", "tortona": "DER", "cremona": "CRE",
    "udine": "UDI", "treviso": "TRV", "cantu": "CANT", "cantù": "CANT",
    "brescia": "BRE", "varese": "VAR", "reggio em": "REG",
    "reggio emilia": "REG", "trieste": "TRI",
    # Long forms (legacy / sponsor variants — substring fallback icin)
    "olimpia milano": "MILA", "ea7 milano": "MILA",
    "ea7 emporio armani milano": "MILA", "armani milano": "MILA",
    "olimpia": "MILA", "ax armani exchange milano": "MILA",
    "virtus bologna": "VIRT", "segafredo bologna": "VIRT",
    "virtus segafredo bologna": "VIRT", "virtus": "VIRT", "bologna": "VIRT",
    "reyer venezia": "REY", "umana reyer venezia": "REY", "reyer": "REY",
    "aquila basket trento": "TRT", "dolomiti energia trento": "TRT",
    "dolomiti energia trentino": "TRT", "trentino": "TRT", "aquila": "TRT",
    "dinamo sassari": "SASS", "banco di sardegna sassari": "SASS",
    "dinamo bds sassari": "SASS", "dinamo": "SASS",
    "napoli basket": "NAP", "gevi napoli basket": "NAP",
    "trapani shark": "TRP", "trapani sharks": "TRP",
    "sportinvest trapani sharks": "TRP",
    "derthona basket": "DER", "bertram derthona tortona": "DER",
    "bertram yachts derthona tortona": "DER", "derthona": "DER",
    "vanoli cremona": "CRE", "vanoli basket cremona": "CRE", "vanoli": "CRE",
    "amici pallacanestro udinese": "UDI", "apu udine": "UDI",
    "old wild west udine": "UDI", "udinese": "UDI",
    "universo treviso basket": "TRV", "nutribullet treviso": "TRV",
    "nutribullet treviso basket": "TRV", "treviso basket": "TRV",
    "pallacanestro cantu": "CANT", "acqua san bernardo cantu": "CANT",
    "acqua s.bernardo cantu": "CANT",
    "pallacanestro brescia": "BRE", "germani brescia": "BRE",
    "germani brescia leonessa": "BRE", "germani": "BRE",
    "pallacanestro varese": "VAR", "openjobmetis varese": "VAR",
    "itelyum varese": "VAR", "openjobmetis": "VAR",
    "pallacanestro reggiana": "REG", "unahotels reggio emilia": "REG",
    "reggiana": "REG", "reggio": "REG",
    "pallacanestro trieste": "TRI", "pallacanestro trieste 2004": "TRI",
    "allianz pallacanestro trieste": "TRI",
}


class LegaScraper(EuropeanBasketScraper):
    """Lega Basket Serie A eurobasket.com scraper."""

    SOURCE = "lega_scraper"
    BASE_URL = "https://www.eurobasket.com/Italy/basketball-Serie-A.aspx"

    def _fetch_html(self, season: str) -> str:  # noqa: ARG002 — URL sezon bagimsiz
        return self._http_get(self.BASE_URL)

    def _parse_teams(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        teams: set[str] = set()
        # Game row'larindan team isimlerini cek (sayfa team-only listesi vermiyor).
        for el in soup.select("td.GamesTeam, td.GamesTeamC"):
            name = el.get_text(" ", strip=True).lower()
            abbr = _name_to_abbr(name)
            if abbr:
                teams.add(abbr)
        return sorted(teams)

    def _parse_games(self, html: str) -> list[ScrapedGame]:
        soup = BeautifulSoup(html, "html.parser")
        games: list[ScrapedGame] = []
        # Eurobasket game row: <tr> ile GamesResult <td> icerir.
        # Birden fazla selector fallback (BS4 :has eski versiyonlarda yok).
        rows = soup.select("tr:has(td.GamesResult)")
        if not rows:
            rows = [
                r for r in soup.select("tr")
                if r.find("td", class_="GamesResult")
            ]
        for row in rows:
            game = _parse_one_game(row)
            if game is not None:
                games.append(game)
        return games


# ── Helpers (modul-level, test edilebilir) ──

_SCORE_RE = re.compile(r"(\d{2,3})\s*[-–]\s*(\d{2,3})")
_ENGLISH_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
# Eurobasket format: "Jun.1:" / "May 28:" / "Oct.15:"
_DATE_RE = re.compile(r"([A-Z][a-z]{2})\.?\s*(\d{1,2}):?", re.IGNORECASE)

# Italyanca ay isimleri → ay numarasi (1-12). Eurobasket Ingilizce kullaniyor
# ama eski test fixture'lari + olasi sezon disi varyant icin destek korunur.
_ITALIAN_MONTHS: dict[str, int] = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4,
    "maggio": 5, "giugno": 6, "luglio": 7, "agosto": 8,
    "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
}
_DATE_ITALIAN_RE = re.compile(
    r"(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|"
    r"luglio|agosto|settembre|ottobre|novembre|dicembre)"
    r"(?:\s+(\d{4}))?",
    re.IGNORECASE,
)


def _name_to_abbr(name: str) -> str | None:
    """Takim ismini standart kisaltmaya cevir (LONGEST MATCH first).

    Eurobasket varyantlari noktalama icerebilir ("Reggio Em.", "Virtus BO").
    Trailing nokta + bosluk normalize edilir.
    """
    norm = name.strip().lower().rstrip(".").strip()
    if not norm:
        return None
    if norm in _LEGA_NAME_TO_ABBR:
        return _LEGA_NAME_TO_ABBR[norm]
    # Substring fallback — uzun ismi once kontrol et
    for known, abbr in sorted(
        _LEGA_NAME_TO_ABBR.items(), key=lambda kv: -len(kv[0])
    ):
        if known in norm:
            return abbr
    return None


def _parse_english_short_date(s: str, default_year: int) -> datetime | None:
    """Eurobasket date format: "Jun.1:" / "May 28:" → datetime(default_year, ...).

    Yil yok — caller default_year geçer (current season year).
    """
    m = _DATE_RE.search(s)
    if not m:
        return None
    month = _ENGLISH_MONTHS.get(m.group(1).lower())
    if month is None:
        return None
    day = int(m.group(2))
    try:
        return datetime(default_year, month, day, tzinfo=timezone.utc)
    except ValueError:
        return None


def _parse_italian_date(s: str, default_year: int) -> datetime | None:
    """Italyanca tarih string'ini datetime'a cevir (legacy fixture destegi).

    Kabul formatlari:
      "12 giugno 2026"
      "12 giugno"           → default_year kullanilir
      "12 GIUGNO 2026"      → case-insensitive
    """
    m = _DATE_ITALIAN_RE.search(s.lower())
    if not m:
        return None
    day = int(m.group(1))
    month = _ITALIAN_MONTHS.get(m.group(2).lower())
    if month is None:
        return None
    year = int(m.group(3)) if m.group(3) else default_year
    try:
        return datetime(year, month, day, tzinfo=timezone.utc)
    except ValueError:
        # Gecersiz tarih (ornek "32 giugno") — sessiz skip, caller filter yapar
        return None


def _parse_one_game(row) -> ScrapedGame | None:
    """Tek bir mac row'undan ScrapedGame uret (parse fail → None, sessiz skip).

    Eurobasket row format:
      <tr><td class="GamesDate">Jun.1:</td>
          <td class="GamesTeam TextAlignRight"><b>Virtus BO</b></td>
          <td class="GamesResult"><a>&nbsp;98-79&nbsp;</a></td>
          <td class="GamesTeam TextAlignLeft">Venezia</td>
          <td class="MediaGuide"></td></tr>

    Tek bir bozuk row tum scrape'i kirmamali. Coklu fail → games=[] →
    base scraper ZERO_PARSED_DATA korumasi devreye girer.
    """
    date_cell = row.find("td", class_="GamesDate")
    result_cell = row.find("td", class_="GamesResult")
    team_cells = row.find_all(
        "td", class_=lambda c: c and "GamesTeam" in c,
    )
    if not date_cell or not result_cell or len(team_cells) < 2:
        return None

    result_text = result_cell.get_text(" ", strip=True)
    score_m = _SCORE_RE.search(result_text)
    if score_m is None:
        return None
    home_score = int(score_m.group(1))
    away_score = int(score_m.group(2))

    home_name = team_cells[0].get_text(" ", strip=True).lower()
    away_name = team_cells[1].get_text(" ", strip=True).lower()
    home_abbr = _name_to_abbr(home_name)
    away_abbr = _name_to_abbr(away_name)
    if not home_abbr or not away_abbr or home_abbr == away_abbr:
        return None

    date_text = date_cell.get_text(" ", strip=True)
    date_dt = _parse_english_short_date(
        date_text, default_year=datetime.now(timezone.utc).year,
    )
    if date_dt is None:
        return None

    return ScrapedGame(
        date_utc=date_dt,
        home_team=home_abbr,
        away_team=away_abbr,
        home_score=home_score,
        away_score=away_score,
    )
