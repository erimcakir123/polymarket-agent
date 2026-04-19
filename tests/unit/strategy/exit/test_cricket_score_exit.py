"""cricket_score_exit.py unit tests (SPEC-011)."""
from __future__ import annotations

from src.models.enums import ExitReason
from src.strategy.exit.cricket_score_exit import (
    CricketExitResult,
    check,
)


def _score_info(
    innings: int = 2,
    our_chasing: bool = True,
    balls_remaining: int = 60,
    runs_remaining: int = 50,
    wickets_lost: int = 4,
    required_rate: float = 5.0,
) -> dict:
    return {
        "available": True,
        "innings": innings,
        "our_chasing": our_chasing,
        "balls_remaining": balls_remaining,
        "runs_remaining": runs_remaining,
        "wickets_lost": wickets_lost,
        "required_run_rate": required_rate,
    }


# ── Non-exit cases ─────────────────────────────────────────────

def test_available_false_no_exit():
    r = check({"available": False}, current_price=0.3, sport_tag="cricket_ipl")
    assert r is None


def test_innings_1_no_exit():
    r = check(_score_info(innings=1), current_price=0.3, sport_tag="cricket_ipl")
    assert r is None


def test_our_chasing_false_no_exit():
    r = check(
        _score_info(our_chasing=False, balls_remaining=10, runs_remaining=100, required_rate=60),
        current_price=0.85, sport_tag="cricket_ipl",
    )
    assert r is None


def test_chase_won_no_exit():
    r = check(_score_info(runs_remaining=0), current_price=0.9, sport_tag="cricket_ipl")
    assert r is None


def test_normal_chase_no_exit():
    r = check(_score_info(), current_price=0.5, sport_tag="cricket_ipl")
    assert r is None


# ── C1: Impossible RRR ─────────────────────────────────────────

def test_c1_impossible_rrr_triggers():
    r = check(
        _score_info(balls_remaining=24, runs_remaining=80, required_rate=20.0),
        current_price=0.05, sport_tag="cricket_ipl",
    )
    assert r is not None
    assert r.reason == ExitReason.SCORE_EXIT
    assert "C1" in r.detail


def test_c1_rrr_under_threshold_no_exit():
    r = check(
        _score_info(balls_remaining=24, runs_remaining=68, required_rate=17.0),
        current_price=0.10, sport_tag="cricket_ipl",
    )
    assert r is None


def test_c1_balls_over_threshold_no_exit():
    r = check(
        _score_info(balls_remaining=60, runs_remaining=200, required_rate=20.0),
        current_price=0.20, sport_tag="cricket_ipl",
    )
    assert r is None


# ── C2: Too many wickets ───────────────────────────────────────

def test_c2_8_wickets_20_runs_left_triggers():
    r = check(
        _score_info(wickets_lost=8, runs_remaining=25, balls_remaining=30, required_rate=5.0),
        current_price=0.15, sport_tag="cricket_ipl",
    )
    assert r is not None
    assert "C2" in r.detail


def test_c2_7_wickets_no_exit():
    r = check(
        _score_info(wickets_lost=7, runs_remaining=30, balls_remaining=30, required_rate=6.0),
        current_price=0.30, sport_tag="cricket_ipl",
    )
    assert r is None


def test_c2_8_wickets_small_runs_no_exit():
    r = check(
        _score_info(wickets_lost=8, runs_remaining=15, balls_remaining=30, required_rate=3.0),
        current_price=0.60, sport_tag="cricket_ipl",
    )
    assert r is None


# ── C3: Final balls, big gap ───────────────────────────────────

def test_c3_final_balls_big_gap_triggers():
    r = check(
        _score_info(balls_remaining=4, runs_remaining=15, wickets_lost=6, required_rate=22.5),
        current_price=0.05, sport_tag="cricket_ipl",
    )
    assert r is not None
    assert r.reason == ExitReason.SCORE_EXIT


def test_c3_final_balls_small_gap_no_exit():
    r = check(
        _score_info(balls_remaining=4, runs_remaining=8, wickets_lost=5, required_rate=12.0),
        current_price=0.40, sport_tag="cricket_ipl",
    )
    assert r is None


# ── Config driven (ODI) ────────────────────────────────────────

def test_odi_higher_c1_threshold():
    r = check(
        _score_info(balls_remaining=50, runs_remaining=100, required_rate=12.5),
        current_price=0.05, sport_tag="cricket_odi",
    )
    assert r is not None
    assert "C1" in r.detail


def test_odi_t20_rate_no_exit():
    r = check(
        _score_info(balls_remaining=50, runs_remaining=100, required_rate=12.5),
        current_price=0.20, sport_tag="cricket_ipl",
    )
    assert r is None


def test_detail_contains_sport_thresholds():
    r = check(
        _score_info(balls_remaining=24, runs_remaining=80, required_rate=20.0),
        current_price=0.05, sport_tag="cricket_ipl",
    )
    assert r is not None
    assert "rrr=20" in r.detail.lower() or "rrr=20.0" in r.detail.lower()
