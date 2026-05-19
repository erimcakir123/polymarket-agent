"""Feature extractor — player profile + H2H + form extraction."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from src.domain.prediction.feature_extractor import (
    FeatureSnapshot,
    extract_features,
    extract_h2h,
    extract_recent_form,
    match_count_in_window,
)
from src.infrastructure.data.sackmann_csv_client import SackmannMatch


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


def test_match_count_in_window():
    snapshot_date = datetime(2026, 5, 19)
    matches = [
        _make_match("20260301", "A", "B"),
        _make_match("20260201", "A", "C"),
        _make_match("20250601", "A", "D"),
        _make_match("20240501", "A", "E"),  # too old
    ]
    count = match_count_in_window(
        matches, player="A", snapshot_date=snapshot_date, days=365,
    )
    assert count == 3


def test_extract_h2h_no_meetings():
    matches: list[SackmannMatch] = [_make_match("20260101", "X", "Y")]
    h2h = extract_h2h(matches, "A", "B", surface="Hard")
    assert h2h["total"] == 0
    assert h2h["p1_wins"] == 0


def test_extract_h2h_two_meetings_surface_filter():
    matches = [
        _make_match("20260101", "A", "B", surface="Hard"),
        _make_match("20251201", "B", "A", surface="Clay"),
        _make_match("20251101", "A", "B", surface="Hard"),
    ]
    h2h_hard = extract_h2h(matches, "A", "B", surface="Hard")
    assert h2h_hard["total"] == 2
    assert h2h_hard["p1_wins"] == 2

    h2h_all = extract_h2h(matches, "A", "B", surface=None)
    assert h2h_all["total"] == 3
    assert h2h_all["p1_wins"] == 2


def test_extract_recent_form():
    snapshot = datetime(2026, 5, 19)
    matches = [
        _make_match("20260501", "A", "X"),
        _make_match("20260420", "A", "Y"),
        _make_match("20260415", "Z", "A"),
    ]
    form = extract_recent_form(matches, player="A", snapshot_date=snapshot, days=60)
    assert form["wins"] == 2
    assert form["losses"] == 1
    assert form["w_pct"] == pytest.approx(2.0 / 3.0)


def test_extract_features_returns_snapshot():
    snapshot = datetime(2026, 5, 19)
    matches = [
        _make_match("20260501", "A", "B", surface="Clay"),
        _make_match("20260420", "A", "C", surface="Clay"),
    ]
    snap = extract_features(
        matches, p1="A", p2="B", surface="Clay",
        snapshot_date=snapshot,
    )
    assert isinstance(snap, FeatureSnapshot)
    assert snap.p1_match_count_12mo >= 1
    assert snap.p2_match_count_12mo >= 1
    assert snap.surface == "Clay"
    assert snap.h2h_matches_same_surface >= 1
