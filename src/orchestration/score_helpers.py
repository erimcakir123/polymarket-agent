"""Score enricher pure helpers (SPEC-005).

Saf (I/O-free) yardımcı fonksiyonlar — ScoreEnricher tarafından kullanılır.
score_enricher.py'den ayrıştırılarak dosya boyutu ARCH_GUARD limitinde tutulur.
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.domain.matching.pair_matcher import match_pair, match_team
from src.domain.sports.nhl_match_clock import parse_nhl_status
from src.infrastructure.apis.espn_client import ESPNMatchScore
from src.infrastructure.apis.score_client import MatchScore
from src.models.position import Position
from src.orchestration.soccer_score_builder import (
    determine_our_outcome as _soccer_our_outcome,
    is_knockout_competition as _soccer_is_knockout,
)
from src.strategy.enrichment.question_parser import extract_teams


def is_score_sane(
    sport_tag: str,
    ms: MatchScore | ESPNMatchScore,
    min_total: int,
) -> bool:
    """NBA live score sanity guard (PLAN-025).

    Score adapter bazen NBA live maçlarda mantıksız küçük total'ler döndürüyor
    (orl-det Q4 elapsed=%94 score=2-2 → instant-exit phantom). Bu helper:
    - sport_tag != "nba" → her zaman True (kapsam dışı)
    - is_completed=True → True (final skor, ne olursa olsun)
    - home/away None → False (eksik veri)
    - total >= min_total → True; aksi halde False (reject)

    min_total=0 → guard kapalı (development/testing escape hatch).
    """
    if min_total <= 0:
        return True
    if (sport_tag or "").lower() != "nba":
        return True
    if getattr(ms, "is_completed", False):
        return True
    h = ms.home_score
    a = ms.away_score
    if h is None or a is None:
        return False
    return (h + a) >= min_total


def is_within_match_window(pos: Position, window_hours: float) -> bool:
    """Pozisyon maç penceresi içinde mi? (match_start ± window saat)."""
    if not pos.match_start_iso:
        return False
    try:
        start = datetime.fromisoformat(pos.match_start_iso.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return False
    now = datetime.now(timezone.utc)
    diff_hours = abs((now - start).total_seconds()) / 3600.0
    return diff_hours <= window_hours


def resolve_tennis_league(slug: str) -> str:
    """WTA/ATP league resolver: slug "wta-*" ise "wta", aksi halde "atp"."""
    return "wta" if (slug or "").lower().startswith("wta") else "atp"


def slug_country_prefix(slug: str) -> str:
    """Polymarket slug'tan ülke/tournament prefix'ini çıkar.

    Slug formatı: "<prefix>-<...>", örn. "arg-cac-pla-2026-04-20" → "arg".
    Soccer league discovery input'u. Boş/malformed → "".
    """
    if not slug:
        return ""
    return slug.lower().split("-", 1)[0]


def find_match_via_pair(
    pos: Position,
    scores: list,
    home_attr: str,
    away_attr: str,
    min_confidence: float = 0.80,
) -> object | None:
    """pair_matcher kullanarak skor listesinden eşleşen event'i bul.

    home_attr/away_attr: ESPN için "home_name"/"away_name", Odds API için
    "home_team"/"away_team". Aynı logic her iki kaynakta çalışır.

    Pair matching: team_a + team_b verildi → her iki takım da eşlemeli
    (swap destekli). Sadece team_a verildi → single-team fallback.
    """
    team_a, team_b = extract_teams(pos.question)
    if not team_a:
        return None

    best_match = None
    best_conf = 0.0

    for ms in scores:
        home = getattr(ms, home_attr, "") or ""
        away = getattr(ms, away_attr, "") or ""
        if not home or not away:
            continue

        if team_b:
            is_match, conf = match_pair((team_a, team_b), (home, away))
            if is_match and conf > best_conf:
                best_match = ms
                best_conf = conf
        else:
            mh, ch, _ = match_team(team_a, home)
            ma, ca, _ = match_team(team_a, away)
            best_side = max(ch, ca)
            if (mh or ma) and best_side > best_conf:
                best_match = ms
                best_conf = best_side

    return best_match if best_conf >= min_confidence else None


def build_score_info(pos: Position, ms: MatchScore | ESPNMatchScore) -> dict:
    """Eşleşen skor verisinden score_info dict oluştur (direction-aware).

    ESPN: home_name/away_name kullanır + linescores içerir.
    Odds API: home_team/away_team kullanır + linescores boş.
    """
    if ms.home_score is None or ms.away_score is None:
        return {"available": False}

    team_a, _ = extract_teams(pos.question)

    home_field: str = getattr(ms, "home_name", None) or getattr(ms, "home_team", "")
    a_is_home, _, _ = match_team(team_a or "", home_field)

    if a_is_home:
        yes_score, no_score = ms.home_score, ms.away_score
    else:
        yes_score, no_score = ms.away_score, ms.home_score

    if pos.direction == "BUY_YES":
        our_score, opp_score = yes_score, no_score
    else:
        our_score, opp_score = no_score, yes_score

    deficit = opp_score - our_score
    linescores: list = getattr(ms, "linescores", []) or []
    our_is_home = (pos.direction == "BUY_YES") == a_is_home

    result = {
        "available": True,
        "our_score": our_score,
        "opp_score": opp_score,
        "deficit": deficit,
        "period": ms.period,
        "inning": getattr(ms, "inning", None),
        "map_diff": -deficit,
        "linescores": linescores,
        "our_is_home": our_is_home,
        "espn_start": getattr(ms, "commence_time", ""),
        "minute": getattr(ms, "minute", None),
        "regulation_state": getattr(ms, "regulation_state", ""),
        "our_outcome": _soccer_our_outcome(pos),
        "knockout": _soccer_is_knockout(pos),
        "period_number": getattr(ms, "period_number", None),
        "clock_seconds": getattr(ms, "clock_seconds", None),
        "home_team_id": getattr(ms, "home_team_id", ""),
        "away_team_id": getattr(ms, "away_team_id", ""),
        "is_overtime": False,
        "is_shootout": False,
    }

    # NHL: parse raw ESPN status payload via NHLClock to set is_overtime / is_shootout
    sport_tag = (getattr(pos, "sport_tag", "") or "").lower()
    raw_status = getattr(ms, "raw_status", {}) or {}
    if sport_tag in ("nhl", "ahl", "hockey") and raw_status:
        try:
            clock = parse_nhl_status(raw_status)
            result["is_overtime"] = clock.is_overtime
            result["is_shootout"] = clock.is_shootout
        except Exception:
            pass  # keep defaults False — pipeline must not break on parse failure

    return result
