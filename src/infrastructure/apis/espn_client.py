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
    commence_time: str = ""  # ISO start time (ESPN competition date)
    inning: int | None = None  # SPEC-014: MLB/beyzbol inning (status.period int); None = beyzbol degil veya pregame
    minute: int | None = None  # SPEC-015: futbol dakikası (status.displayClock parse); None = futbol değil veya pre
    regulation_state: str = ""  # SPEC-015: futbol "pre" | "in" | "post"
    period_number: int | None = None  # SPEC-A4: NBA/NFL çeyrek int (1-4, 5+=OT); None = NBA/NFL değil veya pre
    clock_seconds: int | None = None  # SPEC-A4: NBA/NFL kalan saniye (status.displayClock "M:SS" parse); None = parse başarısız


def _parse_clock_to_seconds(clock: str) -> int | None:
    """SPEC-A4: ESPN displayClock stringini saniyeye çevir.

    Format: "M:SS" veya "MM:SS" (örn. "5:30" → 330, "12:45" → 765, "0:00" → 0).
    Malformed input veya boş string → None (fail-safe, exit fire etmez).
    """
    if not clock or not isinstance(clock, str):
        return None
    parts = clock.strip().split(":")
    if len(parts) != 2:
        return None
    try:
        minutes = int(parts[0])
        seconds = int(parts[1])
    except (ValueError, TypeError):
        return None
    if minutes < 0 or seconds < 0 or seconds >= 60:
        return None
    return minutes * 60 + seconds


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


def _parse_competition(comp: dict, sport: str = "") -> ESPNMatchScore | None:
    """Tek bir competition dict'ini ESPNMatchScore'a çevir.

    Args:
        comp:  ESPN competition dict.
        sport: ESPN sport slug ("baseball", "hockey", vb.). MLB inning için gerekli.

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

    # SPEC-014: MLB inning from status.period (int field, 1-9+ = inning, 0 = pregame)
    inning: int | None = None
    if sport == "baseball":
        raw_period = status_block.get("period")
        if isinstance(raw_period, int) and raw_period > 0:
            inning = raw_period

    # SPEC-A4: NBA/NFL period (int 1-4, 5+=OT) + clock_seconds (displayClock "M:SS" parse)
    period_number: int | None = None
    clock_seconds: int | None = None
    if sport in ("basketball", "football"):
        raw_period = status_block.get("period")
        if isinstance(raw_period, int) and raw_period > 0:
            period_number = raw_period
        raw_clock = status_block.get("displayClock", "") or ""
        clock_seconds = _parse_clock_to_seconds(raw_clock)

    # SPEC-015: Soccer minute parse from displayClock ("67'", "45+2'", "90'+13'")
    minute: int | None = None
    regulation_state = ""
    if sport == "soccer":
        clock_state: str = type_block.get("state", "")
        regulation_state = clock_state if isinstance(clock_state, str) else ""
        if clock_state == "in":
            clock = status_block.get("displayClock", "") or ""
            # "67'" → 67, "45+2'" → 45, "90'+13'" → 90 (base minute, stoppage ignored)
            clock_stripped = clock.rstrip("'").strip()
            # Handle "90'+13'" → "90+13"
            clock_stripped = clock_stripped.replace("'", "")
            if "+" in clock_stripped:
                base = clock_stripped.split("+")[0]
            else:
                base = clock_stripped
            try:
                minute = int(base)
            except (ValueError, TypeError):
                minute = None

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
        commence_time=str(comp.get("date", "") or ""),
        inning=inning,
        minute=minute,
        regulation_state=regulation_state,
        period_number=period_number,
        clock_seconds=clock_seconds,
    )


def _parse_scoreboard(response: dict, sport: str = "") -> list[ESPNMatchScore]:
    """ESPN scoreboard JSON yanıtını ESPNMatchScore listesine çevir.

    Args:
        response: ESPN API JSON yanıtı.
        sport:    ESPN sport slug ("baseball", "hockey", vb.) — inning parse için gerekli.
    """
    results: list[ESPNMatchScore] = []
    for event in response.get("events", []):
        for grouping in event.get("groupings", []):
            for comp in grouping.get("competitions", []):
                match = _parse_competition(comp, sport=sport)
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
        return _parse_scoreboard(resp.json(), sport=sport)
    except Exception as exc:  # noqa: BLE001
        logger.warning("ESPN scoreboard fetch failed [%s/%s]: %s", sport, league, exc)
        return []
