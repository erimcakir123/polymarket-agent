"""VTB United League (Rusya) scraper — eurobasket.com VTB sayfa parser.

URL: https://www.eurobasket.com/VTB-United-League/basketball.aspx
    (vtb-league.com schedule sayfası tamamen client-side JS — statik scrape
    imkansız. Eurobasket.com VTB için ayrı sayfa veriyor, "GamesDate / GamesTeam /
    GamesResult" CSS class'ları ile temiz tablo. 600+ row, regular season + playoff.)

Date format: eurobasket "Jun.1:" / "May 28:" gibi İngilizce kısaltma.
            Yıl yok → sezon takvimine göre default_year ile doldurulur.

Parse stratejisi: BeautifulSoup ile birden fazla CSS selector dene
(site yapısı değişirse fallback). Eşleşemezse ValueError → base scraper
parse fail → HealthTracker fail → NO_DATA_NO_TRADE devreye girer.

NOT: Eurobasket VTB sayfası VTB-only — diğer ligler karışmıyor. Reserve takım
("-2" suffix) ve youth ("CSKA-Jun.") satırları takım listesinde olmadığı için
otomatik filtreleniyor.
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


# Takım adı → standart kısaltma (resolver _VTB_TEAMS ile hizalı).
# Eurobasket varyantları: "MBA Mos." / "N.Novgoro." / "Uralmas." / "Lokomoti."
_VTB_NAME_TO_ABBR: dict[str, str] = {
    "cska": "CSKA", "pbc cska": "CSKA", "cska moscow": "CSKA",
    "zenit": "ZEN", "bc zenit": "ZEN", "zenit saint petersburg": "ZEN",
    "unics": "UNI", "bc unics": "UNI", "unics kazan": "UNI",
    "lokomotiv": "LOK", "lokomoti": "LOK", "lokomotiv kuban": "LOK",
    "pbc lokomotiv kuban": "LOK", "loko": "LOK",
    "parma": "PARMA", "bc parma": "PARMA", "parma-p": "PARMA",
    "betcity parma": "PARMA",
    "avtodor": "AVT", "bc avtodor": "AVT", "avtodor saratov": "AVT",
    "mba": "MBA", "mba mos": "MBA", "mba moscow": "MBA", "mba-mai": "MBA",
    "uralmash": "URA", "uralmas": "URA", "bc uralmash": "URA",
    "uralmash yekaterinburg": "URA",
    "nizhny novgorod": "NIZ", "n.novgoro": "NIZ", "n.novgo": "NIZ",
    "bc nizhny novgorod": "NIZ", "pari nizhniy novgorod": "NIZ",
    "samara": "SAMA", "bc samara": "SAMA",
    "enisey": "ENI", "bc enisey": "ENI", "enisey krasnoyarsk": "ENI",
    "minsk": "MNSK", "cmoki-minsk": "MNSK",
}


class VtbScraper(EuropeanBasketScraper):
    """VTB United League eurobasket.com scraper."""

    SOURCE = "vtb_scraper"
    BASE_URL = "https://www.eurobasket.com/VTB-United-League/basketball.aspx"

    def _fetch_html(self, season: str) -> str:  # noqa: ARG002 — URL sezon bağımsız
        return self._http_get(self.BASE_URL)

    def _parse_teams(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        teams: set[str] = set()
        # Game row'larından team isimlerini çek (sayfa team-only listesi vermiyor).
        for el in soup.select("td.GamesTeam, td.GamesTeamC"):
            name = el.get_text(" ", strip=True).lower()
            abbr = _name_to_abbr(name)
            if abbr:
                teams.add(abbr)
        return sorted(teams)

    def _parse_games(self, html: str) -> list[ScrapedGame]:
        soup = BeautifulSoup(html, "html.parser")
        games: list[ScrapedGame] = []
        # Eurobasket game row: <tr> ile GamesResult <td> içerir.
        # Birden fazla selector fallback (site evrim için).
        rows = soup.select("tr:has(td.GamesResult)")
        if not rows:
            # Fallback: BeautifulSoup :has CSS selector eski versiyonlarda yok
            rows = [r for r in soup.select("tr") if r.find("td", class_="GamesResult")]
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


def _name_to_abbr(name: str) -> str | None:
    """Takım ismini standart kısaltmaya çevir (LONGEST MATCH first).

    Eurobasket varyantları noktalama içerir ("MBA Mos.", "Lokomoti.").
    Trailing nokta + boşluk normalize edilir.
    """
    norm = name.strip().lower().rstrip(".").strip()
    if not norm:
        return None
    if norm in _VTB_NAME_TO_ABBR:
        return _VTB_NAME_TO_ABBR[norm]
    # Substring fallback — uzun ismi önce kontrol et
    for known, abbr in sorted(_VTB_NAME_TO_ABBR.items(), key=lambda kv: -len(kv[0])):
        if known in norm:
            # Reserve takım filtresi: "-2" veya "jun" suffix'i Junior takımı
            if "-2" in norm or "jun" in norm:
                return None
            return abbr
    return None


def _parse_english_short_date(s: str, default_year: int) -> datetime | None:
    """Eurobasket date format: "Jun.1:" / "May 28:" → datetime(default_year, ...).

    Yıl yok — caller default_year geçer (current season year).
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


def _parse_one_game(row) -> ScrapedGame | None:
    """Tek bir mac row'undan ScrapedGame uret (parse fail → None, sessiz skip).

    Eurobasket row format:
      <tr><td class="GamesDate">Jun.1:</td>
          <td class="GamesTeam TextAlignRight"><b>Zenit</b></td>
          <td class="GamesResult"><a>&nbsp;82-80&nbsp;</a></td>
          <td class="GamesTeam TextAlignLeft">Lokomotiv</td>
          <td class="MediaGuide"></td></tr>

    Tek bir bozuk row tum scrape'i kirmamali. Coklu fail → games=[] →
    base scraper bunu success sayar (sezon dışı varsayımı).
    """
    date_cell = row.find("td", class_="GamesDate")
    result_cell = row.find("td", class_="GamesResult")
    team_cells = row.find_all("td", class_=lambda c: c and "GamesTeam" in c)
    if not date_cell or not result_cell or len(team_cells) < 2:
        return None

    result_text = result_cell.get_text(" ", strip=True)
    score_m = _SCORE_RE.search(result_text)
    if score_m is None:
        return None
    # Eurobasket layout: GamesResult solunda HOME (RightAlign) sağında AWAY (LeftAlign)
    # ama score "home-away" olarak yazılı. Test edilmiş örnek: Zenit 82-80 Lokomotiv
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
