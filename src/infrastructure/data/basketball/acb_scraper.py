"""Liga Endesa (ACB) scraper — eurobasket.com Spain sayfa parser.

URL: https://www.eurobasket.com/Spain/basketball-Liga-ACB.aspx
    (acb.com/calendario tamamen JS-rendered + ağır anti-bot katmanı; eurobasket
    Spain için ayrı sayfa veriyor, "GamesDate / GamesTeam / GamesResult" CSS
    class'ları ile temiz tablo. 300+ row, regular season + playoff. Aynı paterni
    BSL ve VTB için de kullanıyoruz — siteyle ilgili tek doğruluk kaynağı.)

Date format: eurobasket "Jun.1:" / "May 28:" gibi İngilizce kısaltma.
            Yıl yok → sezon takvimine göre default_year ile doldurulur.

Parse stratejisi: BeautifulSoup ile GamesDate/GamesTeam/GamesResult class'ları
ile selector. Site yapısı değişirse parse fail → HealthTracker fail →
NO_DATA_NO_TRADE devreye girer (basketball_dispatch ACB slug'ı reddeder).

NOT: Eurobasket Spain sayfası ACB-only — diğer İspanyol ligleri (LEB) ayrı
sayfalarda. Henüz oynanmamış maçlar "----" skor ile gelir, SCORE_RE eşleşmediği
için sessizce atlanır (sadece tamamlanmış maçlar Glicko'ya gider).
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


# Takım adı → standart kısaltma (resolver _ACB_TEAMS ile hizalı).
# Eurobasket kısaltmalı varyantlar veriyor ("Real Mad.", "Rio Breo.", "Gran Cana.")
# — substring match + trailing-dot normalize ile karşılıyoruz.
# Polymarket alias = lowercase abbr token (örn "rea" Real Madrid için Polymarket'ta).
_ACB_NAME_TO_ABBR: dict[str, str] = {
    "real madrid": "RM", "real mad": "RM", "madrid": "RM",
    "barcelona": "FCB", "barça": "FCB", "fc barcelona": "FCB", "barca": "FCB",
    "valencia": "VAL", "valencia basket": "VAL",
    "baskonia": "BAS", "vitoria": "BAS",
    "basket zaragoza": "ZAR", "zaragoza": "ZAR", "casademont zaragoza": "ZAR",
    "casademont": "ZAR",
    "unicaja": "UCM", "malaga": "UCM",
    "tenerife": "LEN", "lenovo tenerife": "LEN", "la laguna": "LEN",
    "la laguna tenerife": "LEN",
    "gran canaria": "GCA", "gran cana": "GCA", "dreamland gran canaria": "GCA",
    "bilbao": "BIL", "surne bilbao": "BIL", "bilbao basket": "BIL",
    "joventut": "JOV", "badalona": "JOV",
    "manresa": "MAN", "baxi manresa": "MAN",
    "murcia": "MUR", "ucam murcia": "MUR",
    "granada": "GRA", "covirán granada": "GRA", "coviran granada": "GRA",
    "palencia": "ZUN", "zunder palencia": "ZUN",
    "girona": "GIR", "bàsquet girona": "GIR", "basquet girona": "GIR",
    "breogán": "BTV", "breogan": "BTV", "río breogán": "BTV",
    "rio breogan": "BTV", "rio breo": "BTV", "lugo": "BTV",
    "burgos": "BUR", "burgos sp": "BUR", "san pablo burgos": "BUR",
    "lleida": "LLE", "hiopos lleida": "LLE",
    "andorra": "AND", "morabanc andorra": "AND", "bc andorra": "AND",
}


class AcbScraper(EuropeanBasketScraper):
    """ACB Liga Endesa eurobasket.com scraper."""

    SOURCE = "acb_scraper"
    BASE_URL = "https://www.eurobasket.com/Spain/basketball-Liga-ACB.aspx"

    def _fetch_html(self, season: str) -> str:  # noqa: ARG002 — URL sezon bağımsız
        return self._http_get(self.BASE_URL)

    def _parse_teams(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        teams: set[str] = set()
        # Game row'larından team isimlerini çek (eurobasket team-only listesi yok).
        for el in soup.select("td.GamesTeam, td.GamesTeamC"):
            name = el.get_text(" ", strip=True).lower()
            abbr = _name_to_abbr(name)
            if abbr:
                teams.add(abbr)
        return sorted(teams)

    def _parse_games(self, html: str) -> list[ScrapedGame]:
        soup = BeautifulSoup(html, "html.parser")
        games: list[ScrapedGame] = []
        # Eurobasket game row: <tr> GamesResult <td> içerir.
        # :has selector eski bs4'lerde yok — try/fallback.
        rows = soup.select("tr:has(td.GamesResult)")
        if not rows:
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

# Eski acb.com Spanish date format hâlâ destekleniyor (test geriye uyumluluğu +
# acb.com fallback olası kullanım). "2 de junio de 2026" / "15 de marzo".
_SPANISH_MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}
_DATE_SPANISH_RE = re.compile(
    r"(\d{1,2})\s+de\s+(\w+)(?:\s+de\s+(\d{4}))?", re.IGNORECASE,
)


def _name_to_abbr(name: str) -> str | None:
    """Takım ismini standart kısaltmaya çevir (LONGEST MATCH first).

    Eurobasket varyantları noktalama içerir ("Real Mad.", "Rio Breo.").
    Trailing nokta + boşluk normalize edilir.
    """
    norm = name.strip().lower().rstrip(".").strip()
    if not norm:
        return None
    if norm in _ACB_NAME_TO_ABBR:
        return _ACB_NAME_TO_ABBR[norm]
    # Substring fallback — uzun ismi önce kontrol et ("la laguna tenerife" > "tenerife").
    for known, abbr in sorted(_ACB_NAME_TO_ABBR.items(), key=lambda kv: -len(kv[0])):
        if known in norm:
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


def _parse_spanish_date(s: str, default_year: int) -> datetime | None:
    """Eski acb.com format: '2 de junio de 2026' / '15 de marzo'.

    Fallback için tutuluyor — birincil kaynak eurobasket (İngilizce kısa).
    """
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

    Eurobasket row format:
      <tr><td class="GamesDate">Jun.2:</td>
          <td class="GamesTeam TextAlignRight">Murcia</td>
          <td class="GamesResult TextAlignCenter">68-91</td>
          <td class="GamesTeam TextAlignLeft"><b>Barca</b></td>
          <td class="MediaGuide"></td></tr>

    Henüz oynanmamış maç: GamesResult = "----" → SCORE_RE eşleşmez → None.
    Tek bir bozuk row tüm scrape'i kırmamalı.
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
    # Layout: home (RightAlign) | score | away (LeftAlign). Skor "home-away".
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
        # Spanish fallback (acb.com legacy / future use)
        date_dt = _parse_spanish_date(
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
