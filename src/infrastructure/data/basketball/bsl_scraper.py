"""Türkiye BSL (Basketbol Süper Ligi) scraper — eurobasket.com results parser.

URL: https://www.eurobasket.com/Turkey/basketball-Super-League.aspx
Resolution kaynagi gamma'da tbl.org.tr ama o site Cloudflare arkasi (refuse);
eurobasket.com public HTML + chronological results table sunuyor.

Parse stratejisi: AcbScraper paralelinde — birden fazla CSS selector dene,
eslesemezse ValueError → base scraper parse fail → HealthTracker fail →
NO_DATA_NO_TRADE devreye girer (basketball_dispatch BSL slug'i reddeder).

Tarih formati: Tukrce ay isimleri (Ocak..Aralik) + ek olarak Ingilizce kisa
("May 16" gibi) çünkü eurobasket çok dilli yayinlayabiliyor.
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


# Takim adi (tam/abbreviated/Turkce karakterli) → standart kisaltma.
# Eurobasket "Bahcese." gibi noktali kisaltmalar veriyor → substring match.
# Resolver _BSL_TEAMS ile tam hizali (Polymarket abbr convention).
_BSL_NAME_TO_ABBR: dict[str, str] = {
    "besiktas": "BES", "beşiktaş": "BES",
    "bahcesehir": "BAH", "bahçeşehir": "BAH", "bahcese": "BAH",
    "fenerbahce": "FEN", "fenerbahçe": "FEN", "fenerba": "FEN",
    "anadolu efes": "ANA", "anadolu e": "ANA", "efes": "ANA",
    "galatasaray": "GAL", "galatasa": "GAL",
    "turk telekom": "TUR", "türk telekom": "TUR",
    "petkim": "PET", "petkim spor": "PET",
    "tofas": "TOF", "tofaş": "TOF",
    "trabzonspor": "TRA", "trabzon": "TRA",
    "manisa": "MNS", "manisa bb": "MNS", "glint manisa": "MNS",
    "karsiyaka": "KAR", "karşıyaka": "KAR",
    "bursaspor": "BUR", "bursa": "BUR",
    "merkezefendi": "MER2", "yukatel merkezefendi": "MER2",
    "esenler": "ESE", "erokspor": "ESE", "safiport erokspor": "ESE",
    "mersin": "MER", "mersin msk": "MER", "mersin bsb": "MER",
    "buyukcekmece": "BUY", "büyükçekmece": "BUY", "onvo": "BUY",
}


class BslScraper(EuropeanBasketScraper):
    """BSL eurobasket.com results page scraper."""

    SOURCE = "bsl_scraper"
    BASE_URL = "https://www.eurobasket.com/Turkey/basketball-Super-League.aspx"

    def _fetch_html(self, season: str) -> str:  # noqa: ARG002 — sezon URL parametresi yok
        return self._http_get(self.BASE_URL)

    def _parse_teams(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        teams: set[str] = set()
        # Coklu selector fallback — eurobasket site evrim toleransi.
        for el in soup.select("a[href*='/Turkey/'], a[href*='Team'], .team-name, .equipo"):
            name = el.get_text(strip=True).lower()
            abbr = _name_to_abbr(name)
            if abbr:
                teams.add(abbr)
        return sorted(teams)

    def _parse_games(self, html: str) -> list[ScrapedGame]:
        soup = BeautifulSoup(html, "html.parser")
        games: list[ScrapedGame] = []
        # Coklu selector — div/tr/li tum varyantlar denenir.
        rows = soup.select(".game-row, .match-row, .result-row")
        if not rows:
            # Eurobasket flat HTML — her game ayri div, score-pattern ile tarayalim.
            rows = [d for d in soup.find_all("div") if _SCORE_RE.search(d.get_text(" ", strip=True))]
        for row in rows:
            game = _parse_one_game(row)
            if game is not None:
                games.append(game)
        return games


# ── Helpers (modul-level, test edilebilir) ──

_SCORE_RE = re.compile(r"\[?\s*(\d{2,3})\s*[-–]\s*(\d{2,3})\s*\]?")

# Turkce ay isimleri (full) + Ingilizce kisa (eurobasket bazen "May 16" kullaniyor).
_TURKISH_MONTHS = {
    "ocak": 1, "şubat": 2, "subat": 2, "mart": 3, "nisan": 4,
    "mayıs": 5, "mayis": 5, "haziran": 6, "temmuz": 7, "ağustos": 8, "agustos": 8,
    "eylül": 9, "eylul": 9, "ekim": 10, "kasım": 11, "kasim": 11, "aralık": 12, "aralik": 12,
}
_ENGLISH_SHORT_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
# "12 Haziran 2026" / "12 Haziran" / "Jun.2" / "May 16" patternleri
_DATE_TR_RE = re.compile(r"(\d{1,2})\s+(\w+)(?:\s+(\d{4}))?", re.IGNORECASE)
_DATE_EN_RE = re.compile(r"([A-Za-z]{3,9})\.?\s*(\d{1,2})(?:[,\s]+(\d{4}))?")


def _name_to_abbr(name: str) -> str | None:
    """Takim ismini standart kisaltmaya cevir (LONGEST MATCH first)."""
    name = name.strip().lower()
    if not name:
        return None
    if name in _BSL_NAME_TO_ABBR:
        return _BSL_NAME_TO_ABBR[name]
    # Substring fallback — uzun ismi once kontrol et ("glint manisa" > "manisa")
    for known, abbr in sorted(_BSL_NAME_TO_ABBR.items(), key=lambda kv: -len(kv[0])):
        if known in name:
            return abbr
    return None


def _parse_turkish_date(s: str, default_year: int) -> datetime | None:
    """Turkce ('12 Haziran 2026') veya Ingilizce kisa ('Jun.2') tarih parse."""
    # Once Turkce: "12 Haziran [2026]"
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
    # Ingilizce kisa: "May 16" / "Jun.2"
    m2 = _DATE_EN_RE.search(s)
    if m2:
        month_str, day_str, year_str = m2.group(1).lower()[:3], m2.group(2), m2.group(3)
        month = _ENGLISH_SHORT_MONTHS.get(month_str)
        if month is not None:
            try:
                year = int(year_str) if year_str else default_year
                return datetime(year, month, int(day_str), tzinfo=timezone.utc)
            except ValueError:
                return None
    return None


def _parse_one_game(row) -> ScrapedGame | None:
    """Tek bir mac row'undan ScrapedGame uret (parse fail → None, sessiz skip).

    Tek bozuk row scrape'in tamamini kirmamali. Eksik takim/score/tarih → None.
    Ust katman None'lari filtreler — kaliteli sayim icin.
    """
    text = row.get_text(" ", strip=True)
    score_m = _SCORE_RE.search(text)
    if score_m is None:
        return None
    try:
        home_score = int(score_m.group(1))
        away_score = int(score_m.group(2))
    except ValueError:
        return None
    # Takim isimlerini icindeki linklerden/text node'lardan cek.
    team_names: list[str] = []
    for el in row.select("a, .team-name, .equipo"):
        n = el.get_text(strip=True).lower()
        if n:
            team_names.append(n)
    if not team_names:
        # Link yoksa, text'i score etrafinda parcala (eurobasket flat-div fallback)
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
