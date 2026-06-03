"""Türkiye BSL (Basketbol Süper Ligi) scraper — eurobasket.com results parser.

URL: https://www.eurobasket.com/Turkey/basketball-Super-League.aspx

Sayfa yapısı VTB ile birebir aynı: "GamesDate / GamesTeam / GamesResult" CSS
class'lı `<tr>` satırları. Tarih formatı İngilizce kısa: "Jun.2:" / "May 30:".
Eurobasket takım isimlerini noktalı kısaltarak yayınlıyor ("Bahcese.",
"Fenerba.", "Turk Tele.", "Trabzons.", "Merkezefe.").

Parse stratejisi: VtbScraper paralelinde — `tr:has(td.GamesResult)` selector +
fallback. Eşleşemezse base scraper ZERO_PARSED_DATA tetikler → HealthTracker
fail → NO_DATA_NO_TRADE (basketball_dispatch BSL slug'i reddeder).
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


# Takım adı → standart kısaltma (resolver _BSL_TEAMS ile hizalı).
# Eurobasket gerçek varyantları (doğrulanmış 2026-06-02):
#   "Bahcese.", "Fenerba.", "Anadolu E", "Galatasa.", "Turk Tele.",
#   "Trabzons.", "Merkezefe.", "Mersin S.", "Buyukcekm.", "Erokspor"
# Hem tam form hem eurobasket-kısa form ekli ki substring fallback gerekmeden
# direkt eşleşsin.
_BSL_NAME_TO_ABBR: dict[str, str] = {
    "besiktas": "BES", "beşiktaş": "BES",
    "bahcesehir": "BAH", "bahçeşehir": "BAH", "bahcese": "BAH",
    "fenerbahce": "FEN", "fenerbahçe": "FEN", "fenerba": "FEN",
    "anadolu efes": "ANA", "anadolu e": "ANA", "efes": "ANA",
    "galatasaray": "GAL", "galatasa": "GAL",
    "turk telekom": "TUR", "türk telekom": "TUR", "turk tele": "TUR",
    "petkim": "PET", "petkim spor": "PET",
    "tofas": "TOF", "tofaş": "TOF",
    "trabzonspor": "TRA", "trabzon": "TRA", "trabzons": "TRA",
    "manisa": "MNS", "manisa bb": "MNS", "glint manisa": "MNS",
    "karsiyaka": "KAR", "karşıyaka": "KAR",
    "bursaspor": "BUR", "bursa": "BUR",
    "merkezefendi": "MER2", "yukatel merkezefendi": "MER2", "merkezefe": "MER2",
    "esenler": "ESE", "erokspor": "ESE", "safiport erokspor": "ESE",
    "mersin": "MER", "mersin msk": "MER", "mersin bsb": "MER", "mersin s": "MER",
    "buyukcekmece": "BUY", "büyükçekmece": "BUY", "onvo": "BUY", "buyukcekm": "BUY",
}


class BslScraper(EuropeanBasketScraper):
    """BSL eurobasket.com results page scraper (VTB ile aynı tablo yapısı)."""

    SOURCE = "bsl_scraper"
    BASE_URL = "https://www.eurobasket.com/Turkey/basketball-Super-League.aspx"

    def _fetch_html(self, season: str) -> str:  # noqa: ARG002 — sezon URL parametresi yok
        return self._http_get(self.BASE_URL)

    def _parse_teams(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        teams: set[str] = set()
        # Asıl path (eurobasket tablo): game row'larındaki team hücrelerinden çek.
        for el in soup.select("td.GamesTeam"):
            name = el.get_text(" ", strip=True).lower()
            abbr = _name_to_abbr(name)
            if abbr:
                teams.add(abbr)
        # Fallback (flat-div fixture): /Turkey/ link metinlerinden çek.
        if not teams:
            for el in soup.select("a[href*='/Turkey/'], .team-name"):
                name = el.get_text(strip=True).lower()
                abbr = _name_to_abbr(name)
                if abbr:
                    teams.add(abbr)
        return sorted(teams)

    def _parse_games(self, html: str) -> list[ScrapedGame]:
        soup = BeautifulSoup(html, "html.parser")
        games: list[ScrapedGame] = []
        # Eurobasket game row: <tr> içinde GamesResult <td> var.
        # Birden fazla selector fallback (CSS :has eski bs4'te yok diye).
        rows = soup.select("tr:has(td.GamesResult)")
        if not rows:
            rows = [r for r in soup.select("tr") if r.find("td", class_="GamesResult")]
        # Eski Turkish flat-div fixture'ları için ek fallback (test geriye uyumluluğu).
        if not rows:
            rows = [
                d for d in soup.find_all("div")
                if _SCORE_RE.search(d.get_text(" ", strip=True))
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
_TURKISH_MONTHS = {
    "ocak": 1, "şubat": 2, "subat": 2, "mart": 3, "nisan": 4,
    "mayıs": 5, "mayis": 5, "haziran": 6, "temmuz": 7,
    "ağustos": 8, "agustos": 8, "eylül": 9, "eylul": 9,
    "ekim": 10, "kasım": 11, "kasim": 11, "aralık": 12, "aralik": 12,
}
# Eurobasket asıl format: "Jun.2:" / "May 30:"
_DATE_EN_RE = re.compile(r"([A-Za-z]{3,9})\.?\s*(\d{1,2})(?:[,\s]+(\d{4}))?")
# Eski Türkçe fixture'lar / olası yerel format için fallback: "12 Haziran 2026"
_DATE_TR_RE = re.compile(r"(\d{1,2})\s+(\w+)(?:\s+(\d{4}))?", re.IGNORECASE)


def _name_to_abbr(name: str) -> str | None:
    """Takım ismini standart kısaltmaya çevir (LONGEST MATCH first).

    Eurobasket varyantları trailing nokta içeriyor ("Bahcese.", "Fenerba.").
    Normalize: strip + lower + trailing nokta sil + bold tag artığı temizle.
    """
    norm = name.strip().lower().rstrip(".").strip()
    if not norm:
        return None
    if norm in _BSL_NAME_TO_ABBR:
        return _BSL_NAME_TO_ABBR[norm]
    # Substring fallback — uzun ismi önce kontrol et ("glint manisa" > "manisa")
    for known, abbr in sorted(_BSL_NAME_TO_ABBR.items(), key=lambda kv: -len(kv[0])):
        if known in norm:
            return abbr
    return None


def _parse_english_short_date(s: str, default_year: int) -> datetime | None:
    """Eurobasket date format: "Jun.2:" / "May 30:" → datetime(default_year, ...)."""
    m = _DATE_EN_RE.search(s)
    if not m:
        return None
    month = _ENGLISH_MONTHS.get(m.group(1).lower()[:3])
    if month is None:
        return None
    try:
        day = int(m.group(2))
        year = int(m.group(3)) if m.group(3) else default_year
        return datetime(year, month, day, tzinfo=timezone.utc)
    except ValueError:
        return None


def _parse_turkish_date(s: str, default_year: int) -> datetime | None:
    """Türkçe ('12 Haziran 2026') veya İngilizce kısa ('Jun.2') tarih parse.

    Önce Türkçe formatı dener (eski fixture geriye uyumluluğu), yoksa
    İngilizce kısa formuna düşer (eurobasket asıl format).
    """
    m = _DATE_TR_RE.search(s.lower())
    if m:
        day_str, month_str, year_str = m.group(1), m.group(2).lower(), m.group(3)
        month = _TURKISH_MONTHS.get(month_str)
        if month is not None:
            try:
                year = int(year_str) if year_str else default_year
                return datetime(year, month, int(day_str), tzinfo=timezone.utc)
            except ValueError:
                return None
    return _parse_english_short_date(s, default_year)


def _parse_one_game(row) -> ScrapedGame | None:
    """Tek bir mac row'undan ScrapedGame uret (parse fail → None, sessiz skip).

    Eurobasket row formati (VTB ile birebir):
      <tr><td class="GamesDate">Jun.2:</td>
          <td class="GamesTeam TextAlignRight"><b>Besiktas</b></td>
          <td class="GamesResult TextAlignCenter"><a>&nbsp;82-79&nbsp;</a></td>
          <td class="GamesTeam TextAlignLeft">Bahcese.</td>
          <td class="MediaGuide"></td></tr>

    Eski fixture (flat-div, score+takim text) için fallback path da çalışır.
    Tek bozuk row tum scrape'i kirmamali.
    """
    # Önce tablo path'i (gerçek eurobasket sayfası).
    date_cell = row.find("td", class_="GamesDate") if hasattr(row, "find") else None
    result_cell = row.find("td", class_="GamesResult") if hasattr(row, "find") else None
    if date_cell and result_cell:
        team_cells = row.find_all(
            "td", class_=lambda c: c and "GamesTeam" in c,
        )
        if len(team_cells) < 2:
            return None
        score_m = _SCORE_RE.search(result_cell.get_text(" ", strip=True))
        if score_m is None:
            return None
        try:
            home_score = int(score_m.group(1))
            away_score = int(score_m.group(2))
        except ValueError:
            return None
        home_abbr = _name_to_abbr(team_cells[0].get_text(" ", strip=True).lower())
        away_abbr = _name_to_abbr(team_cells[1].get_text(" ", strip=True).lower())
        if not home_abbr or not away_abbr or home_abbr == away_abbr:
            return None
        date_dt = _parse_turkish_date(
            date_cell.get_text(" ", strip=True),
            default_year=datetime.now(timezone.utc).year,
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

    # Fallback: flat-div / link-içi takım isimleri (eski fixture davranışı).
    text = row.get_text(" ", strip=True)
    score_m = _SCORE_RE.search(text)
    if score_m is None:
        return None
    try:
        home_score = int(score_m.group(1))
        away_score = int(score_m.group(2))
    except ValueError:
        return None
    team_names: list[str] = []
    for el in row.select("a, .team-name"):
        n = el.get_text(strip=True).lower()
        if n:
            team_names.append(n)
    if not team_names:
        before, after = text[: score_m.start()], text[score_m.end():]
        team_names = [before.strip().lower(), after.strip().lower()]
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
    date_dt = _parse_turkish_date(text, default_year=datetime.now(timezone.utc).year)
    if date_dt is None:
        return None
    return ScrapedGame(
        date_utc=date_dt,
        home_team=home_abbr,
        away_team=away_abbr,
        home_score=home_score,
        away_score=away_score,
    )
