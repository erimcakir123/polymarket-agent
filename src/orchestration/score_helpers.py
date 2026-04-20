"""Score enricher pure helpers (SPEC-005).

Saf (I/O-free) yardımcı fonksiyonlar — ScoreEnricher tarafından kullanılır.
score_enricher.py'den ayrıştırılarak dosya boyutu ARCH_GUARD limitinde tutulur.
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.domain.matching.pair_matcher import match_pair, match_team
from src.infrastructure.apis.espn_client import ESPNMatchScore
from src.infrastructure.apis.score_client import MatchScore
from src.models.position import Position
from src.orchestration.soccer_score_builder import (
    determine_our_outcome as _soccer_our_outcome,
    is_knockout_competition as _soccer_is_knockout,
)
from src.strategy.enrichment.question_parser import extract_teams


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

    return {
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
    }
