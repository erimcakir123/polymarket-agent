"""Cricket match state → score_info dict (SPEC-011).

CricAPI CricketMatchScore nesnesinden, position direction'a gore,
cricket_score_exit'in tukettigi score_info dict'i uretir. Pure — CricAPI
response VE position verilir, dict doner. I/O yok (orchestration dispatch-only).

Ayri dosya gerekcesi: score_enricher.py 367 satir, cricket branch eklenirse
400 asilir (ARCH_GUARD Kural 3). Cricket-specific logic burada yasar.
"""
from __future__ import annotations

from src.domain.matching.pair_matcher import match_pair, match_team
from src.infrastructure.apis.cricket_client import CricketMatchScore
from src.strategy.enrichment.question_parser import extract_teams

_FORMAT_MAX_OVERS: dict[str, int] = {"t20": 20, "t20i": 20, "odi": 50}
_MIN_MATCH_CONFIDENCE = 0.80


def find_cricket_match(pos, matches: list[CricketMatchScore]) -> CricketMatchScore | None:
    """Pair matcher ile pozisyon-match eslestir. None → uygun eslesme yok."""
    team_a, team_b = extract_teams(pos.question)
    if not team_a:
        return None

    best_match: CricketMatchScore | None = None
    best_conf = 0.0

    for m in matches:
        if len(m.teams) < 2:
            continue
        home, away = m.teams[0], m.teams[1]
        if team_b:
            is_match, conf = match_pair((team_a, team_b), (home, away))
            if is_match and conf > best_conf:
                best_match = m
                best_conf = conf
        else:
            mh, ch, _ = match_team(team_a, home)
            ma, ca, _ = match_team(team_a, away)
            best_side = max(ch, ca)
            if (mh or ma) and best_side > best_conf:
                best_match = m
                best_conf = best_side

    return best_match if best_conf >= _MIN_MATCH_CONFIDENCE else None


def build_cricket_score_info(pos, match: CricketMatchScore) -> dict:
    """CricAPI match → score_info dict. cricket_score_exit bunu tuketir."""
    if not match.match_started or not match.innings:
        return {"available": False}

    team_a, team_b = extract_teams(pos.question)
    direction = getattr(pos, "direction", "BUY_YES")
    # BUY_YES → we support team_a winning; BUY_NO → we support team_b winning
    our_team_name = team_a if direction == "BUY_YES" else (team_b or "")

    max_overs = _FORMAT_MAX_OVERS.get(match.match_type.lower(), 20)
    max_balls = max_overs * 6

    if len(match.innings) < 2:
        return {"available": True, "innings": 1}

    first = match.innings[0]
    second = match.innings[1]
    target = int(first.get("runs", 0)) + 1

    runs_scored = int(second.get("runs", 0))
    wickets_lost = int(second.get("wickets", 0))
    overs_float = float(second.get("overs", 0))

    # Overs "15.3" format = 15 overs + 3 balls
    full_overs = int(overs_float)
    partial_balls = int(round((overs_float - full_overs) * 10))
    if partial_balls > 5:
        partial_balls = 5
    balls_faced = full_overs * 6 + partial_balls

    runs_remaining = max(0, target - runs_scored)
    balls_remaining = max(0, max_balls - balls_faced)

    required_rate = (runs_remaining * 6.0 / balls_remaining) if balls_remaining > 0 else 0.0
    current_rate = (runs_scored * 6.0 / balls_faced) if balls_faced > 0 else 0.0

    batting_team = first.get("team", "")
    chasing_team = second.get("team", "")
    our_chasing = False
    if our_team_name and chasing_team and batting_team:
        _, bat_conf, _ = match_team(our_team_name, batting_team)
        _, chase_conf, _ = match_team(our_team_name, chasing_team)
        # Our team is chasing only if chase_conf clearly leads batting_conf
        our_chasing = chase_conf >= _MIN_MATCH_CONFIDENCE and chase_conf > bat_conf

    return {
        "available": True,
        "innings": 2,
        "target": target,
        "runs_remaining": runs_remaining,
        "balls_remaining": balls_remaining,
        "wickets_lost": wickets_lost,
        "required_run_rate": required_rate,
        "current_run_rate": current_rate,
        "our_chasing": our_chasing,
    }
