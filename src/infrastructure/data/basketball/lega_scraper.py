"""Lega Basket Serie A (Italya) scraper — legabasket.it calendar HTML parser.

URL: https://www.legabasket.it/lba/8/calendario-e-risultati (sezon takvimi + sonuclar).

Parse stratejisi: BeautifulSoup ile birden fazla CSS selector dene
(site yapisi degisirse fallback). Eslesemezse ValueError → base scraper
parse fail → HealthTracker fail → NO_DATA_NO_TRADE devreye girer.

AcbScraper paraleli (ayni pattern, Italyanca tarih + Italyan takim isimleri).

NOT: Bu scraper canli site dogrulamasi bekliyor. legabasket.it React-rendered
(JS dinamik) olabilir; o durumda BeautifulSoup statik HTML'de mac satirlarini
goremez ve games=[] doner. Production'da HTML yapisi degisirse parse fail →
3-strike sonra "broken" → telegram alert (mevcut HealthTracker akisi).
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
# Polymarket slug abbreviation'lari aynisi kullanilir; site farkli isim
# varyantlari verebilir (Olimpia Milano / EA7 Emporio Armani / Armani Milano).
_LEGA_NAME_TO_ABBR: dict[str, str] = {
    "olimpia milano": "MILA", "ea7 milano": "MILA", "armani milano": "MILA",
    "ea7 emporio armani milano": "MILA", "milano": "MILA", "olimpia": "MILA",
    "virtus bologna": "VIRT", "segafredo bologna": "VIRT", "virtus": "VIRT",
    "reyer venezia": "REY", "umana reyer venezia": "REY", "reyer": "REY",
    "aquila basket trento": "TRT", "dolomiti energia trento": "TRT",
    "trentino": "TRT", "trento": "TRT", "aquila": "TRT",
    "dinamo sassari": "SASS", "banco di sardegna sassari": "SASS",
    "sassari": "SASS", "dinamo": "SASS",
    "napoli basket": "NAP", "givova scafati": "NAP", "napoli": "NAP",
    "trapani shark": "TRP", "trapani": "TRP",
    "derthona basket": "DER", "bertram derthona tortona": "DER",
    "tortona": "DER", "derthona": "DER",
    "vanoli cremona": "CRE", "vanoli basket cremona": "CRE",
    "cremona": "CRE", "vanoli": "CRE",
    "amici pallacanestro udinese": "UDI", "apu udine": "UDI",
    "udinese": "UDI", "udine": "UDI",
    "universo treviso basket": "TRV", "nutribullet treviso": "TRV",
    "treviso": "TRV", "treviso basket": "TRV",
    "pallacanestro cantu": "CANT", "acqua san bernardo cantu": "CANT",
    "cantu": "CANT", "cantù": "CANT",
    "pallacanestro brescia": "BRE", "germani brescia": "BRE",
    "brescia": "BRE", "germani": "BRE",
    "pallacanestro varese": "VAR", "openjobmetis varese": "VAR",
    "varese": "VAR", "openjobmetis": "VAR",
    "pallacanestro reggiana": "REG", "unahotels reggio emilia": "REG",
    "reggio emilia": "REG", "reggiana": "REG", "reggio": "REG",
    "pallacanestro trieste": "TRI", "pallacanestro trieste 2004": "TRI",
    "trieste": "TRI",
}


class LegaScraper(EuropeanBasketScraper):
    """Lega Basket Serie A calendar scraper."""

    SOURCE = "lega_scraper"
    BASE_URL = "https://www.legabasket.it/lba/8/calendario-e-risultati"

    def _fetch_html(self, season: str) -> str:  # noqa: ARG002 — season URL'e bagli degil (cari sezon)
        return self._http_get(self.BASE_URL)

    def _parse_teams(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        teams: set[str] = set()
        # Birden fazla selector pattern (site evrim için fallback).
        for el in soup.select(
            "[data-team], .team-name, .nome-squadra, .squadra, "
            ".team, a[href*='squadre']"
        ):
            name = el.get_text(strip=True).lower()
            abbr = _name_to_abbr(name)
            if abbr:
                teams.add(abbr)
        return sorted(teams)

    def _parse_games(self, html: str) -> list[ScrapedGame]:
        soup = BeautifulSoup(html, "html.parser")
        games: list[ScrapedGame] = []
        # Mac row icin coklu selector fallback (site evrim icin).
        rows = soup.select(".partita")
        if not rows:
            rows = soup.select(".match-row")
        if not rows:
            rows = soup.select(".game-row")
        if not rows:
            rows = soup.select(".calendar-game")
        if not rows:
            rows = soup.select("[data-partita]")
        if not rows:
            rows = soup.select(".incontro")
        for row in rows:
            game = _parse_one_game(row)
            if game is not None:
                games.append(game)
        return games


# ── Helpers (modul-level, test edilebilir) ──

_SCORE_RE = re.compile(r"(\d{2,3})\s*[-–]\s*(\d{2,3})")

# Italyanca ay isimleri → ay numarasi (1-12).
_ITALIAN_MONTHS: dict[str, int] = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4,
    "maggio": 5, "giugno": 6, "luglio": 7, "agosto": 8,
    "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
}

# "12 giugno 2026" veya "12 giugno" (yil opsiyonel) — Italyanca tarih pattern.
# Ay grubu sadece BILINEN Italyanca ay isimleri — score "85 - 78" + "3 giugno"
# concat olunca regex "78 X" + "3 giugno" arasinda yanlis match yapmasin diye
# ay isimleri pattern'in icine alternation olarak yerlestirildi.
_DATE_ITALIAN_RE = re.compile(
    r"(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|"
    r"luglio|agosto|settembre|ottobre|novembre|dicembre)"
    r"(?:\s+(\d{4}))?",
    re.IGNORECASE,
)


def _name_to_abbr(name: str) -> str | None:
    """Takim ismini standart kisaltmaya cevir (LONGEST MATCH first)."""
    name = name.strip().lower()
    if not name:
        return None
    if name in _LEGA_NAME_TO_ABBR:
        return _LEGA_NAME_TO_ABBR[name]
    # Substring fallback — uzun ismi once kontrol et
    # (ornek "milano" < "olimpia milano" ama site "EA7 Milano" verebilir)
    for known, abbr in sorted(
        _LEGA_NAME_TO_ABBR.items(), key=lambda kv: -len(kv[0])
    ):
        if known in name:
            return abbr
    return None


def _parse_italian_date(s: str, default_year: int) -> datetime | None:
    """Italyanca tarih string'ini datetime'a cevir.

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
    for el in row.select(
        "a[href*='squadre'], .nome-squadra, .team-name, "
        ".squadra, [data-team]"
    ):
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
    # Tarih: row icinde Italyanca tarih ara, yoksa None → skip.
    date_dt = _parse_italian_date(
        text, default_year=datetime.now(timezone.utc).year,
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
