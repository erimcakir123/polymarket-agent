"""LAB v2: NBA/WNBA rest days adjustment.

Back-to-back oynayan takim icin Elo'ya gecici penalty uygular.
Akademik: BG to game performans 5-10% dusus (Kubatko et al, BBR 2013+).

Yaklasim:
  - rest_days = 0 (ayni gun aslinda imkansiz ama theoretical)
  - rest_days = 1 (back-to-back) → -30 Elo penalty
  - rest_days = 2 → -10 Elo
  - rest_days >= 3 → no penalty

Implementation: factory'de basketball_ratings yuklendikten sonra,
schedule cache'inden son maclari oku, gecici Elo'lari hesapla, bunlari
basketball_dispatch'e enjekte et.

Main bot UNTOUCHED.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.domain.pricing.basketball.team_elo import EloRating

_BACK_TO_BACK_PENALTY = 30.0   # Elo points
_TWO_DAY_PENALTY = 10.0
_REST_DAY_THRESHOLD_HOURS = (24.0, 48.0)  # 0-24h=B2B, 24-48h=close, 48+ ok


def compute_rest_penalty(hours_since_last_game: float) -> float:
    """Hours since team's last game → Elo penalty (positive number to subtract)."""
    if hours_since_last_game < _REST_DAY_THRESHOLD_HOURS[0]:
        return _BACK_TO_BACK_PENALTY
    if hours_since_last_game < _REST_DAY_THRESHOLD_HOURS[1]:
        return _TWO_DAY_PENALTY
    return 0.0


def apply_rest_adjustment(
    base_ratings: dict[str, dict[str, EloRating]],
    last_game_iso: dict[str, dict[str, str]],
    now: datetime,
) -> dict[str, dict[str, EloRating]]:
    """Rating dict + last-game iso dict → penalty-adjusted ratings (yeni dict).

    base_ratings: {league: {team: EloRating}}
    last_game_iso: {league: {team: ISO timestamp string of last game}}

    Returns new dict (base ratings unchanged — pure function).
    """
    adjusted: dict[str, dict[str, EloRating]] = {}
    for league, teams in base_ratings.items():
        adjusted[league] = {}
        league_schedule = last_game_iso.get(league, {})
        for team, rating in teams.items():
            iso = league_schedule.get(team)
            if not iso:
                adjusted[league][team] = rating
                continue
            try:
                last_dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
                hours = (now - last_dt).total_seconds() / 3600.0
            except (ValueError, TypeError):
                adjusted[league][team] = rating
                continue
            penalty = compute_rest_penalty(hours)
            if penalty > 0:
                from dataclasses import replace
                adjusted[league][team] = replace(
                    rating, rating=rating.rating - penalty,
                )
            else:
                adjusted[league][team] = rating
    return adjusted


def load_last_game_iso(schedule_path: Path) -> dict[str, dict[str, str]]:
    """Schedule cache'inden son maclari oku.

    Format: {league: {team_abbr: "2026-06-01T20:00:00Z"}}
    Dosya yoksa bos dict.
    """
    if not schedule_path.exists():
        return {}
    try:
        return json.loads(schedule_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def adjust_ratings_now(
    base_ratings: dict[str, dict[str, EloRating]],
    schedule_path: Path,
) -> dict[str, dict[str, EloRating]]:
    """Convenience: schedule yukle + simdiki zamana gore adjust."""
    schedule = load_last_game_iso(schedule_path)
    return apply_rest_adjustment(
        base_ratings, schedule, datetime.now(timezone.utc),
    )
