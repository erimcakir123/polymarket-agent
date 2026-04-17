"""ESPN public scoreboard istemcisi (SPEC-005 Task 1).

Endpoint: https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard
API key gerektirmez.

Desteklenen sporlar: hokey (goals), tenis (set + game), beyzbol, basketbol.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

_ESPN_BASE_URL = "https://site.api.espn.com/apis/site/v2/sports"
_HTTP_TIMEOUT = 10
# Tenis tespiti: herhangi bir linescore değeri bu eşiğin üzerindeyse
# bu tenis değil (futbol, hokey, beyzbol toplam sayısı daha düşük kalır).
# Tenis setleri 0-7 arasında oynanır; 6+ değer = tenis.
_TENNIS_SET_SCORE_MIN = 6


@dataclass
class ESPNMatchScore:
    """ESPN scoreboard API'den gelen tek bir maçın skor bilgisi."""

    event_id: str
    home_name: str
    away_name: str
    home_score: int | None
    away_score: int | None
    period: str           # "Final", "In Progress", ""
    is_completed: bool
    is_live: bool
    last_updated: str
    linescores: list[list[int]] = field(default_factory=list)  # [[home, away], ...] per period


def _is_tennis(linescores: list[list[int]]) -> bool:
    """Herhangi bir dönem skorunda >= 6 varsa tenis olarak kabul et."""
    for pair in linescores:
        if any(v >= _TENNIS_SET_SCORE_MIN for v in pair):
            return True
    return False


def _compute_totals(
    linescores: list[list[int]],
    tennis: bool,
) -> tuple[int | None, int | None]:
    """Toplam skor hesapla.

    Tenis: kazanılan set sayısı (home > away olan dönemler).
    Diğer: tüm dönemlerin toplamı.
    """
    if not linescores:
        return None, None

    if tennis:
        home_sets = sum(1 for h, a in linescores if h > a)
        away_sets = sum(1 for h, a in linescores if a > h)
        return home_sets, away_sets

    home_total = sum(h for h, _ in linescores)
    away_total = sum(a for _, a in linescores)
    return home_total, away_total


def _parse_competition(comp: dict) -> ESPNMatchScore | None:
    """Tek bir competition dict'ini ESPNMatchScore'a çevir.

    Döndürür None → competitor sayısı < 2 veya home/away bulunamadı.
    """
    competitors: list[dict] = comp.get("competitors", [])
    if len(competitors) < 2:
        return None

    home: dict | None = None
    away: dict | None = None
    for c in competitors:
        if c.get("homeAway") == "home":
            home = c
        elif c.get("homeAway") == "away":
            away = c

    if home is None or away is None:
        return None

    # Linescore çiftlerini oluştur: [[home_period, away_period], ...]
    home_ls = home.get("linescores") or []
    away_ls = away.get("linescores") or []
    n_periods = max(len(home_ls), len(away_ls))
    linescores: list[list[int]] = []
    for i in range(n_periods):
        h_val = int(home_ls[i]["value"]) if i < len(home_ls) else 0
        a_val = int(away_ls[i]["value"]) if i < len(away_ls) else 0
        linescores.append([h_val, a_val])

    tennis = _is_tennis(linescores)
    home_score, away_score = _compute_totals(linescores, tennis)

    status_block = comp.get("status", {})
    type_block = status_block.get("type", {})
    description: str = type_block.get("description", "")
    is_completed: bool = bool(type_block.get("completed", False))
    state: str = type_block.get("state", "")
    is_live: bool = state == "in"

    return ESPNMatchScore(
        event_id=str(comp.get("id", "")),
        home_name=home.get("athlete", {}).get("displayName", ""),
        away_name=away.get("athlete", {}).get("displayName", ""),
        home_score=home_score,
        away_score=away_score,
        period=description,
        is_completed=is_completed,
        is_live=is_live,
        last_updated="",
        linescores=linescores,
    )


def _parse_scoreboard(response: dict) -> list[ESPNMatchScore]:
    """ESPN scoreboard JSON yanıtını ESPNMatchScore listesine çevir."""
    results: list[ESPNMatchScore] = []
    for event in response.get("events", []):
        for grouping in event.get("groupings", []):
            for comp in grouping.get("competitions", []):
                match = _parse_competition(comp)
                if match is not None:
                    results.append(match)
    return results


def fetch_scoreboard(
    sport: str,
    league: str,
    date: str | None = None,
) -> list[ESPNMatchScore]:
    """ESPN public scoreboard API'den maç skorlarını çek.

    Args:
        sport:  ESPN sport slug, örn. "hockey", "tennis", "baseball"
        league: ESPN league slug, örn. "nhl", "atp", "mlb"
        date:   YYYYMMDD formatında tarih; None → bugün (ESPN default)

    Returns:
        ESPNMatchScore listesi. Herhangi bir hata → boş liste + WARNING log.
    """
    url = f"{_ESPN_BASE_URL}/{sport}/{league}/scoreboard"
    params: dict[str, str] = {}
    if date is not None:
        params["dates"] = date

    try:
        resp = httpx.get(url, params=params, timeout=_HTTP_TIMEOUT)
        resp.raise_for_status()
        return _parse_scoreboard(resp.json())
    except Exception as exc:  # noqa: BLE001
        logger.warning("ESPN scoreboard fetch failed [%s/%s]: %s", sport, league, exc)
        return []
