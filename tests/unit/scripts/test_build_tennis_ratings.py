"""Smoke test for build_tennis_ratings batch."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from src.infrastructure.data.sackmann_csv_client import SackmannMatch
from scripts.build_tennis_ratings import build_ratings_from_matches


def _make_match(date_str: str, winner: str, loser: str, surface: str = "Hard") -> SackmannMatch:
    return SackmannMatch(
        tourney_id="", tourney_name="", surface=surface, draw_size=32, tourney_level="A",
        match_date=datetime.strptime(date_str, "%Y%m%d"),
        match_num=1,
        winner_id=winner, winner_name=winner, winner_hand="R",
        loser_id=loser, loser_name=loser, loser_hand="R",
        score="6-3 6-4", best_of=3, round="F",
        minutes=None,
        w_ace=None, w_df=None, w_svpt=None, w_1stIn=None, w_1stWon=None,
        w_2ndWon=None, w_SvGms=None, w_bpSaved=None, w_bpFaced=None,
        l_ace=None, l_df=None, l_svpt=None, l_1stIn=None, l_1stWon=None,
        l_2ndWon=None, l_SvGms=None, l_bpSaved=None, l_bpFaced=None,
        winner_rank=None, winner_rank_points=None,
        loser_rank=None, loser_rank_points=None,
    )


def test_build_ratings_creates_player_profiles():
    matches = [
        _make_match("20260101", "A", "B"),
        _make_match("20260102", "A", "C"),
        _make_match("20260103", "B", "A"),
    ]
    ratings = build_ratings_from_matches(
        matches, snapshot_date=datetime(2026, 5, 19),
    )
    assert "A" in ratings
    assert "B" in ratings
    # A more matches → some rating ≠ 1500
    assert ratings["A"].overall.rating != 1500
    # match_count_12mo computed
    assert ratings["A"].match_count_12mo >= 2


def test_build_ratings_empty_returns_empty():
    ratings = build_ratings_from_matches(
        [], snapshot_date=datetime(2026, 5, 19),
    )
    assert ratings == {}
