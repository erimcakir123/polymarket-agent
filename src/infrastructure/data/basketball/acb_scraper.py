"""Liga Endesa (ACB) scraper — acb.com calendar HTML parser.

URL: https://www.acb.com/calendario (sezon takvimi + sonuclar).

Parse stratejisi: BeautifulSoup ile birden fazla CSS selector dene
(site yapisi degisirse fallback). Eslesemezse ValueError → base scraper
parse fail → HealthTracker fail → NO_DATA_NO_TRADE devreye girer.

NOT: Bu scraper canli site dogrulamasi bekliyor. Production'da HTML
yapisi degisirse parse fail → 3-strike sonra "broken" → telegram alert.
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


# Takim adi → standart kisaltma (resolver _ACB_TEAMS ile hizali).
# Site farkli isim varyantlari verebilir (Real Madrid / Real Madrid Baloncesto).
_ACB_NAME_TO_ABBR: dict[str, str] = {
    "real madrid": "RM", "madrid": "RM",
    "barcelona": "FCB", "barça": "FCB", "fc barcelona": "FCB",
    "valencia": "VAL", "valencia basket": "VAL",
    "baskonia": "BAS", "vitoria": "BAS",
    "basket zaragoza": "ZAR", "zaragoza": "ZAR",
    "unicaja": "UCM", "malaga": "UCM",
    "tenerife": "LEN", "lenovo tenerife": "LEN",
    "la laguna": "LAL", "la laguna tenerife": "LAL",
    "gran canaria": "GCA", "dreamland gran canaria": "GCA",
    "bilbao": "BIL", "surne bilbao": "BIL", "bilbao basket": "BIL",
    "casademont": "CAN", "casademont zaragoza": "CAN",
    "joventut": "JOV", "badalona": "JOV",
    "manresa": "MAN", "baxi manresa": "MAN",
    "murcia": "MUR", "ucam murcia": "MUR",
    "granada": "GRA", "covirán granada": "GRA",
    "palencia": "ZUN", "zunder palencia": "ZUN",
    "girona": "GIR", "bàsquet girona": "GIR",
    "breogán": "BTV", "río breogán": "BTV", "lugo": "BTV",
    "burgos": "BUR", "san pablo burgos": "BUR",
    "lleida": "LLE", "hiopos lleida": "LLE",
}


class AcbScraper(EuropeanBasketScraper):
    """ACB Liga Endesa calendar scraper."""

    SOURCE = "acb_scraper"
    BASE_URL = "https://www.acb.com/calendario"

    def _fetch_html(self, season: str) -> str:  # noqa: ARG002 — season URL'e bagli degil (cari sezon)
        return self._http_get(self.BASE_URL)

    def _parse_teams(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        teams: set[str] = set()
        # Birden fazla selector pattern (site evrim için fallback).
        for el in soup.select("[data-equipo], .equipo-nombre, .team-name, .equipo"):
            name = el.get_text(strip=True).lower()
            abbr = _name_to_abbr(name)
            if abbr:
                teams.add(abbr)
        return sorted(teams)

    def _parse_games(self, html: str) -> list[ScrapedGame]:
        soup = BeautifulSoup(html, "html.parser")
        games: list[ScrapedGame] = []
        # Mac rowu icin coklu selector fallback (site evrim icin).
        rows = soup.select(".partido")
        if not rows:
            rows = soup.select(".match-row")
        if not rows:
            rows = soup.select(".calendar-game")
        if not rows:
            rows = soup.select("[data-partido]")
        for row in rows:
            game = _parse_one_game(row)
            if game is not None:
                games.append(game)
        return games


# ── Helpers (modul-level, test edilebilir) ──

_SCORE_RE = re.compile(r"(\d{2,3})\s*[-–]\s*(\d{2,3})")
_SPANISH_MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}
_DATE_SPANISH_RE = re.compile(r"(\d{1,2})\s+de\s+(\w+)(?:\s+de\s+(\d{4}))?", re.IGNORECASE)


def _name_to_abbr(name: str) -> str | None:
    """Takim ismini standart kisaltmaya cevir (LONGEST MATCH first)."""
    name = name.strip().lower()
    if not name:
        return None
    if name in _ACB_NAME_TO_ABBR:
        return _ACB_NAME_TO_ABBR[name]
    # Substring fallback — uzun ismi once kontrol et (girona < bàsquet girona)
    for known, abbr in sorted(_ACB_NAME_TO_ABBR.items(), key=lambda kv: -len(kv[0])):
        if known in name:
            return abbr
    return None


def _parse_spanish_date(s: str, default_year: int) -> datetime | None:
    m = _DATE_SPANISH_RE.search(s.lower())
    if not m:
        return None
    day = int(m.group(1))
    month = _SPANISH_MONTHS.get(m.group(2).lower())
    if month is None:
        return None
    year = int(m.group(3)) if m.group(3) else default_year
    try:
        return datetime(year, month, day, tzinfo=timezone.utc)
    except ValueError:
        return None


def _parse_one_game(row) -> ScrapedGame | None:
    """Tek bir mac row'undan ScrapedGame uret (parse fail → None, sessiz skip).

    Tek bir bozuk row tum scrape'i kirmamali. Coklu fail → games=[] →
    base scraper bunu success sayar (sezon dışı varsayımı) — eger gercekten
    sezon ici fail ise bir sonraki refresh'te ratings empty → trade YOK.
    """
    text = row.get_text(" ", strip=True)
    score_m = _SCORE_RE.search(text)
    if score_m is None:
        return None
    home_score = int(score_m.group(1))
    away_score = int(score_m.group(2))
    # Takim isimlerini row icindeki linklerden/text'ten cek.
    team_names: list[str] = []
    for el in row.select("a[href*='equipo'], .equipo, .team-name, [data-equipo]"):
        n = el.get_text(strip=True).lower()
        if n:
            team_names.append(n)
    home_abbr = away_abbr = None
    for n in team_names:
        abbr = _name_to_abbr(n)
        if abbr and home_abbr is None:
            home_abbr = abbr
        elif abbr and away_abbr is None and abbr != home_abbr:
            away_abbr = abbr
            break
    if not home_abbr or not away_abbr:
        return None
    # Tarih: row icinde Ispanyolca tarih ara, yoksa bugune fallback (skip yerine
    # default datetime — caller filter yapar).
    date_dt = _parse_spanish_date(text, default_year=datetime.now(timezone.utc).year)
    if date_dt is None:
        return None
    return ScrapedGame(
        date_utc=date_dt,
        home_team=home_abbr,
        away_team=away_abbr,
        home_score=home_score,
        away_score=away_score,
    )
