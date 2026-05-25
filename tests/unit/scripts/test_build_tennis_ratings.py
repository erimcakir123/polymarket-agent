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
        atp_main=matches, wta_main=[], snapshot_date=datetime(2026, 5, 19),
    )
    assert "atp:A" in ratings
    assert "atp:B" in ratings
    # A more matches → some rating ≠ 1500
    assert ratings["atp:A"].overall.rating != 1500
    # singles_main_count_12mo computed (main draw)
    assert ratings["atp:A"].singles_main_count_12mo >= 2
    # No ITF / doubles in this scenario
    assert ratings["atp:A"].singles_itf_count_12mo == 0
    assert ratings["atp:A"].doubles_count_12mo == 0


def test_build_ratings_empty_returns_empty():
    ratings = build_ratings_from_matches(
        atp_main=[], wta_main=[], snapshot_date=datetime(2026, 5, 19),
    )
    assert ratings == {}


def test_build_ratings_tour_prefix_keys_no_collision() -> None:
    """Players with same name in ATP and WTA must be stored under different keys."""
    atp = [_make_match("20240101", "Williams", "Other ATP")]
    wta = [_make_match("20240101", "Williams", "Other WTA")]
    snap = datetime(2024, 6, 1)
    out = build_ratings_from_matches(atp_main=atp, wta_main=wta, snapshot_date=snap)

    assert "atp:Williams" in out
    assert "wta:Williams" in out
    assert out["atp:Williams"].tour == "atp"
    assert out["wta:Williams"].tour == "wta"
    assert out["atp:Williams"].player_name == "Williams"
    assert out["wta:Williams"].player_name == "Williams"


def test_ratings_file_has_minimum_players_after_challenger_expansion() -> None:
    """Regression: Challenger Tour expansion must yield ≥1500 rated players.

    Old count: 817 (ATP main-draw only).
    New count: ~2650 (ATP + Challenger).
    """
    import json
    from pathlib import Path

    root = Path(__file__).resolve()
    ratings_path: Path | None = None
    for parent in root.parents:
        candidate = parent / "data" / "tennis_ratings.json"
        if candidate.exists():
            ratings_path = candidate
            break

    if ratings_path is None:
        raise AssertionError("tennis_ratings.json not found — run scripts/build_tennis_ratings.py first")

    data = json.loads(ratings_path.read_text(encoding="utf-8"))
    assert len(data) >= 1500, f"Expected ≥1500 players after Challenger expansion, got {len(data)}"


def test_itf_matches_move_rating_less_than_main_matches() -> None:
    """ITF matches at itf_weight=0.5 should move player rating ~half as much as same main-draw match."""
    snap = datetime(2024, 6, 1)
    win_match = _make_match("20240101", "Alpha", "Beta")

    # Scenario A: 1 win via main draw, no ITF
    out_main = build_ratings_from_matches(
        atp_main=[win_match], wta_main=[],
        atp_itf=[], wta_itf=[],
        snapshot_date=snap,
    )
    main_alpha_rating = out_main["atp:Alpha"].overall.rating

    # Scenario B: 1 win via ITF only
    out_itf = build_ratings_from_matches(
        atp_main=[], wta_main=[],
        atp_itf=[win_match], wta_itf=[],
        snapshot_date=snap,
    )
    itf_alpha_rating = out_itf["atp:Alpha"].overall.rating

    # Both should move rating UP from baseline 1500. ITF should move LESS.
    assert main_alpha_rating > 1500
    assert itf_alpha_rating > 1500
    main_delta = main_alpha_rating - 1500
    itf_delta = itf_alpha_rating - 1500
    assert itf_delta < main_delta, (
        f"ITF should move rating less: main_delta={main_delta:.2f}, itf_delta={itf_delta:.2f}"
    )
    # Roughly half (allow 30-70% range)
    ratio = itf_delta / main_delta
    assert 0.3 < ratio < 0.7, f"ITF/main delta ratio out of range: {ratio:.3f}"


def test_build_ratings_keeps_old_signature_friendly() -> None:
    """ITF args default to None/[] — existing callers passing only main draws still work."""
    # No-op call — should not crash, return empty dict
    out = build_ratings_from_matches(
        atp_main=[], wta_main=[],
        snapshot_date=datetime(2024, 6, 1),
    )
    assert out == {}
