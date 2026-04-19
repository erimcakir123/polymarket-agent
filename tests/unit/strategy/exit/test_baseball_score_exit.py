"""baseball_score_exit.py unit tests (SPEC-010)."""
from __future__ import annotations

from src.models.enums import ExitReason
from src.strategy.exit.baseball_score_exit import (
    BaseballExitResult,
    _parse_inning,
    check,
)


def _score_info(inning_str: str, our_score: int, opp_score: int) -> dict:
    """Test helper: score_info dict olustur."""
    return {
        "available": True,
        "period": inning_str,
        "deficit": opp_score - our_score,
        "our_score": our_score,
        "opp_score": opp_score,
    }


# ── Parse testleri ─────────────────────────────────────────────

def test_parse_inning_top_1st():
    assert _parse_inning("Top 1st") == 1


def test_parse_inning_bot_5th():
    assert _parse_inning("Bot 5th") == 5


def test_parse_inning_mid_9th():
    assert _parse_inning("Mid 9th") == 9


def test_parse_inning_extra_11th():
    assert _parse_inning("Top 11th") == 11


def test_parse_inning_empty_returns_none():
    assert _parse_inning("") is None


def test_parse_inning_final_returns_none():
    assert _parse_inning("Final") is None


def test_parse_inning_in_progress_returns_none():
    assert _parse_inning("In Progress") is None


# ── M1: Blowout (7th+ + 5 run deficit) ─────────────────────────

def test_m1_blowout_7th_5run_exits():
    info = _score_info("Top 7th", our_score=0, opp_score=5)
    r = check(info, current_price=0.20, sport_tag="mlb")
    assert r is not None
    assert r.reason == ExitReason.SCORE_EXIT
    assert "M1" in r.detail


def test_m1_blowout_7th_4run_no_exit():
    info = _score_info("Top 7th", our_score=0, opp_score=4)
    r = check(info, current_price=0.20, sport_tag="mlb")
    assert r is None


def test_m1_blowout_8th_5run_exits():
    info = _score_info("Bot 8th", our_score=2, opp_score=7)
    r = check(info, current_price=0.10, sport_tag="mlb")
    assert r is not None
    assert "M1" in r.detail


# ── M2: Late big deficit (8th+ + 3 run) ────────────────────────

def test_m2_late_deficit_8th_3run_exits():
    info = _score_info("Top 8th", our_score=2, opp_score=5)
    r = check(info, current_price=0.25, sport_tag="mlb")
    assert r is not None
    assert "M2" in r.detail


def test_m2_late_deficit_8th_2run_no_exit():
    info = _score_info("Top 8th", our_score=3, opp_score=5)
    r = check(info, current_price=0.30, sport_tag="mlb")
    assert r is None


# ── M3: Final inning (9th+ + 1 run) ────────────────────────────

def test_m3_final_inning_1run_exits():
    info = _score_info("Top 9th", our_score=3, opp_score=4)
    r = check(info, current_price=0.15, sport_tag="mlb")
    assert r is not None
    assert "M3" in r.detail


def test_m3_extra_inning_1run_exits():
    info = _score_info("Top 11th", our_score=5, opp_score=6)
    r = check(info, current_price=0.10, sport_tag="mlb")
    assert r is not None
    assert "M3" in r.detail


# ── Non-exit cases ─────────────────────────────────────────────

def test_deficit_zero_no_exit():
    info = _score_info("Top 9th", our_score=3, opp_score=3)
    r = check(info, current_price=0.50, sport_tag="mlb")
    assert r is None


def test_leading_no_exit():
    info = _score_info("Top 9th", our_score=5, opp_score=2)
    r = check(info, current_price=0.90, sport_tag="mlb")
    assert r is None


def test_score_info_unavailable_no_exit():
    info = {"available": False}
    r = check(info, current_price=0.30, sport_tag="mlb")
    assert r is None


def test_period_unparseable_no_exit():
    info = _score_info("In Progress", our_score=1, opp_score=5)
    r = check(info, current_price=0.30, sport_tag="mlb")
    assert r is None


def test_early_inning_big_deficit_no_exit():
    info = _score_info("Top 1st", our_score=0, opp_score=6)
    r = check(info, current_price=0.10, sport_tag="mlb")
    assert r is None


def test_kbo_sport_tag_uses_defaults():
    info = _score_info("Top 9th", our_score=3, opp_score=5)
    r = check(info, current_price=0.10, sport_tag="kbo")
    # 9. inning + 2 run deficit → M3 (default deficit=1) tetiklenmeli
    assert r is not None
    assert "M3" in r.detail
