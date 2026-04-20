"""Soccer score exit unit tests (SPEC-015)."""
from __future__ import annotations

from src.models.enums import ExitReason
from src.strategy.exit.soccer_score_exit import SoccerExitResult, check


def _score_info(
    minute: int | None = 70,
    home_score: int = 0,
    away_score: int = 0,
    our_outcome: str = "home",
    state: str = "in",
    knockout: bool = False,
) -> dict:
    return {
        "available": True,
        "minute": minute,
        "home_score": home_score,
        "away_score": away_score,
        "our_outcome": our_outcome,
        "regulation_state": state,
        "knockout": knockout,
    }


# ── HOME/AWAY ──

def test_first_half_no_exit_even_2goals_down() -> None:
    info = _score_info(minute=40, home_score=0, away_score=2, our_outcome="home")
    assert check(info, sport_tag="soccer") is None


def test_60_minute_2_goals_down_no_exit() -> None:
    info = _score_info(minute=60, home_score=0, away_score=2, our_outcome="home")
    assert check(info, sport_tag="soccer") is None


def test_65_minute_2_goals_down_exits() -> None:
    info = _score_info(minute=65, home_score=0, away_score=2, our_outcome="home")
    r = check(info, sport_tag="soccer")
    assert r is not None
    assert r.reason == ExitReason.SCORE_EXIT
    assert "2_goal" in r.detail.lower()


def test_75_minute_1_goal_down_exits() -> None:
    info = _score_info(minute=75, home_score=0, away_score=1, our_outcome="home")
    r = check(info, sport_tag="soccer")
    assert r is not None
    assert "1_goal" in r.detail.lower()


def test_85_minute_level_no_exit() -> None:
    info = _score_info(minute=85, home_score=1, away_score=1, our_outcome="home")
    assert check(info, sport_tag="soccer") is None


def test_winning_2goals_no_exit() -> None:
    info = _score_info(minute=80, home_score=2, away_score=0, our_outcome="home")
    assert check(info, sport_tag="soccer") is None


def test_away_position_2_goals_down_exits() -> None:
    info = _score_info(minute=70, home_score=2, away_score=0, our_outcome="away")
    r = check(info, sport_tag="soccer")
    assert r is not None


# ── DRAW ──

def test_draw_0_0_at_60_no_exit() -> None:
    info = _score_info(minute=60, home_score=0, away_score=0, our_outcome="draw")
    assert check(info, sport_tag="soccer") is None


def test_draw_0_0_at_70_no_exit() -> None:
    info = _score_info(minute=70, home_score=0, away_score=0, our_outcome="draw")
    assert check(info, sport_tag="soccer") is None


def test_draw_goal_at_75_exits() -> None:
    info = _score_info(minute=75, home_score=1, away_score=0, our_outcome="draw")
    r = check(info, sport_tag="soccer")
    assert r is not None
    assert "draw" in r.detail.lower()


def test_draw_knockout_auto_exit_at_90() -> None:
    info = _score_info(minute=92, home_score=1, away_score=1, our_outcome="draw", knockout=True)
    r = check(info, sport_tag="soccer")
    assert r is not None
    assert "knockout" in r.detail.lower()


def test_draw_league_match_90_no_auto_exit() -> None:
    """Lig maçı 90'+ berabere: NOT knockout → HOLD (ama 75'+ gol varsa exit, bu testte 1-1)."""
    info = _score_info(minute=92, home_score=1, away_score=1, our_outcome="draw", knockout=False)
    # 1-1 var yani goal atilmis, minute 92 >= 75 → draw_goal_late exit tetiklenir
    # Bu davranis dogru cunku draw pozisyon + gol var + late minute
    r = check(info, sport_tag="soccer")
    # Gol atildi, exit beklenir (knockout flag fark etmez 75' sonrasi)
    assert r is not None


def test_draw_league_0_0_at_90_no_exit() -> None:
    """Lig maçı 90' 0-0 + draw pozisyon: knockout flag False + gol yok → HOLD."""
    info = _score_info(minute=92, home_score=0, away_score=0, our_outcome="draw", knockout=False)
    assert check(info, sport_tag="soccer") is None


def test_unavailable_skip() -> None:
    info = {"available": False}
    assert check(info, sport_tag="soccer") is None


def test_pregame_skip() -> None:
    info = _score_info(minute=None, state="pre")
    assert check(info, sport_tag="soccer") is None


def test_missing_minute_skip() -> None:
    info = {"available": True, "minute": None}
    assert check(info, sport_tag="soccer") is None


def test_unknown_sport_skip() -> None:
    """sport_tag 'unknown' → get_sport_config None → skip."""
    info = _score_info(minute=80, home_score=0, away_score=2, our_outcome="home")
    assert check(info, sport_tag="unknown_sport") is None
