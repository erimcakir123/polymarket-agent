"""Tennis feature extractor — pure functions.

Computes player profile, H2H, recent form from Sackmann match list.

Spec: docs/superpowers/specs/2026-05-19-tennis-prediction-lab-design.md §5.4
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from src.infrastructure.data.sackmann_csv_client import SackmannMatch


@dataclass
class FeatureSnapshot:
    """Per-match prediction feature snapshot — saved in diagnostic log."""
    p1_name: str
    p2_name: str
    surface: str
    p1_match_count_12mo: int
    p1_surface_count: int
    p1_form_w_pct_60d: float
    p1_form_data_age_days: int
    p2_match_count_12mo: int
    p2_surface_count: int
    p2_form_w_pct_60d: float
    p2_form_data_age_days: int
    h2h_matches_total: int
    h2h_matches_same_surface: int
    h2h_p1_wins: int
    h2h_last_meeting_days_ago: Optional[int]


def match_count_in_window(
    matches: list[SackmannMatch],
    player: str,
    snapshot_date: datetime,
    days: int,
    surface: Optional[str] = None,
) -> int:
    """Count player's matches in last N days, optionally filtered by surface."""
    cutoff = snapshot_date - timedelta(days=days)
    count = 0
    for m in matches:
        if m.match_date < cutoff or m.match_date > snapshot_date:
            continue
        if surface and m.surface != surface:
            continue
        if m.winner_name == player or m.loser_name == player:
            count += 1
    return count


def extract_h2h(
    matches: list[SackmannMatch],
    p1: str,
    p2: str,
    surface: Optional[str] = None,
) -> dict:
    """Head-to-head record between p1 and p2.

    Returns dict with: total, p1_wins, last_meeting_date (datetime|None).
    """
    p1_wins = 0
    total = 0
    last_meeting: Optional[datetime] = None
    for m in matches:
        if surface and m.surface != surface:
            continue
        is_p1_winner = m.winner_name == p1 and m.loser_name == p2
        is_p2_winner = m.winner_name == p2 and m.loser_name == p1
        if not (is_p1_winner or is_p2_winner):
            continue
        total += 1
        if is_p1_winner:
            p1_wins += 1
        if last_meeting is None or m.match_date > last_meeting:
            last_meeting = m.match_date
    return {"total": total, "p1_wins": p1_wins, "last_meeting_date": last_meeting}


def extract_recent_form(
    matches: list[SackmannMatch],
    player: str,
    snapshot_date: datetime,
    days: int = 60,
) -> dict:
    """Recent W%, last_match_age in last N days."""
    cutoff = snapshot_date - timedelta(days=days)
    wins = 0
    losses = 0
    last_date: Optional[datetime] = None
    for m in matches:
        if m.match_date < cutoff or m.match_date > snapshot_date:
            continue
        if m.winner_name == player:
            wins += 1
            if last_date is None or m.match_date > last_date:
                last_date = m.match_date
        elif m.loser_name == player:
            losses += 1
            if last_date is None or m.match_date > last_date:
                last_date = m.match_date
    total = wins + losses
    return {
        "wins": wins,
        "losses": losses,
        "w_pct": (wins / total) if total > 0 else 0.5,
        "last_match_date": last_date,
    }


def extract_features(
    matches: list[SackmannMatch],
    p1: str,
    p2: str,
    surface: str,
    snapshot_date: datetime,
) -> FeatureSnapshot:
    """Build full feature snapshot for p1 vs p2 prediction."""
    p1_count_12mo = match_count_in_window(matches, p1, snapshot_date, 365)
    p1_surface_count = match_count_in_window(matches, p1, snapshot_date, 365, surface=surface)
    p1_form = extract_recent_form(matches, p1, snapshot_date, days=60)
    p1_age = (
        (snapshot_date - p1_form["last_match_date"]).days
        if p1_form["last_match_date"] else 9999
    )

    p2_count_12mo = match_count_in_window(matches, p2, snapshot_date, 365)
    p2_surface_count = match_count_in_window(matches, p2, snapshot_date, 365, surface=surface)
    p2_form = extract_recent_form(matches, p2, snapshot_date, days=60)
    p2_age = (
        (snapshot_date - p2_form["last_match_date"]).days
        if p2_form["last_match_date"] else 9999
    )

    h2h_all = extract_h2h(matches, p1, p2, surface=None)
    h2h_surface = extract_h2h(matches, p1, p2, surface=surface)
    last_meeting_days = (
        (snapshot_date - h2h_all["last_meeting_date"]).days
        if h2h_all["last_meeting_date"] else None
    )

    return FeatureSnapshot(
        p1_name=p1, p2_name=p2, surface=surface,
        p1_match_count_12mo=p1_count_12mo,
        p1_surface_count=p1_surface_count,
        p1_form_w_pct_60d=p1_form["w_pct"],
        p1_form_data_age_days=p1_age,
        p2_match_count_12mo=p2_count_12mo,
        p2_surface_count=p2_surface_count,
        p2_form_w_pct_60d=p2_form["w_pct"],
        p2_form_data_age_days=p2_age,
        h2h_matches_total=h2h_all["total"],
        h2h_matches_same_surface=h2h_surface["total"],
        h2h_p1_wins=h2h_all["p1_wins"],
        h2h_last_meeting_days_ago=last_meeting_days,
    )
