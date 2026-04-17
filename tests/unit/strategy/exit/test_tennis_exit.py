"""Tennis score-based exit tests (SPEC-006)."""
from __future__ import annotations

from src.models.enums import ExitReason
from src.strategy.exit.tennis_exit import check, TennisExitResult


def _info(
    linescores: list[list[int]] | None = None,
    our_is_home: bool = True,
    available: bool = True,
) -> dict:
    ls = linescores or []
    return {
        "available": available,
        "our_score": 0, "opp_score": 0,
        "deficit": 0, "period": "", "map_diff": 0,
        "linescores": ls, "our_is_home": our_is_home,
    }


# ── T1: Straight set loss approaching ──

def test_t1_straight_set_2_5() -> None:
    """0-1 set + 2. sette 2-5 (deficit 3, total 7) → EXIT."""
    info = _info(linescores=[[3, 6], [2, 5]], our_is_home=True)
    result = check(info, current_price=0.30, sport_tag="tennis")
    assert result is not None
    assert result.reason == ExitReason.SCORE_EXIT
    assert "T1" in result.detail


def test_t1_early_deficit_1_4_hold() -> None:
    """0-1 set + 1-4 (total 5 < 7, deficit 3) → HOLD."""
    info = _info(linescores=[[3, 6], [1, 4]], our_is_home=True)
    result = check(info, current_price=0.30, sport_tag="tennis")
    assert result is None


def test_t1_deficit_4_any_total() -> None:
    """0-1 set + 0-4 (deficit 4) → EXIT regardless of total."""
    info = _info(linescores=[[3, 6], [0, 4]], our_is_home=True)
    result = check(info, current_price=0.30, sport_tag="tennis")
    assert result is not None
    assert "T1" in result.detail


def test_t1_close_set_buffer() -> None:
    """1. set 6-7 tiebreak + 2. set 2-5 → HOLD (close set buffer: 3→4)."""
    info = _info(linescores=[[6, 7], [2, 5]], our_is_home=True)
    result = check(info, current_price=0.30, sport_tag="tennis")
    assert result is None


def test_t1_blowout_no_buffer() -> None:
    """1. set 2-6 blowout + 2. set 2-5 → EXIT (no buffer)."""
    info = _info(linescores=[[2, 6], [2, 5]], our_is_home=True)
    result = check(info, current_price=0.30, sport_tag="tennis")
    assert result is not None
    assert "T1" in result.detail


# ── T2: Decider set loss ──

def test_t2_decider_2_5() -> None:
    """1-1 set + 3. sette 2-5 → EXIT."""
    info = _info(linescores=[[6, 3], [4, 6], [2, 5]], our_is_home=True)
    result = check(info, current_price=0.30, sport_tag="tennis")
    assert result is not None
    assert "T2" in result.detail


def test_t2_decider_deficit_2_hold() -> None:
    """1-1 set + 3. sette 3-5 (deficit 2) → HOLD."""
    info = _info(linescores=[[6, 3], [4, 6], [3, 5]], our_is_home=True)
    result = check(info, current_price=0.30, sport_tag="tennis")
    assert result is None


# ── Edge cases ──

def test_no_score_no_exit() -> None:
    info = _info(available=False)
    assert check(info, current_price=0.10, sport_tag="tennis") is None


def test_winning_no_exit() -> None:
    info = _info(linescores=[[6, 3], [4, 2]], our_is_home=True)
    assert check(info, current_price=0.70, sport_tag="tennis") is None


def test_buy_no_direction_mapping() -> None:
    """BUY_NO: our_is_home=False → linescores flipped."""
    info = _info(linescores=[[6, 3], [5, 2]], our_is_home=False)
    # our_is_home=False → our=[3,2] opp=[6,5]. 0-1 set + 2-5 → T1
    result = check(info, current_price=0.30, sport_tag="tennis")
    assert result is not None
    assert "T1" in result.detail
