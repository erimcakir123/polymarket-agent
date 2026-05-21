import pytest
from src.domain.mlb_submarket.bullpen_segmenter import select_pitcher


def _starter() -> dict[str, float]:
    return {"K": 0.22, "BB": 0.08, "HR": 0.030, "1B": 0.14, "2B": 0.045, "3B": 0.004, "HBP": 0.011, "OUT_IN_PLAY": 0.46}


def _bullpen() -> dict[str, dict[str, float]]:
    return {
        "middle": {"K": 0.24, "BB": 0.09, "HR": 0.032, "1B": 0.14, "2B": 0.045, "3B": 0.004, "HBP": 0.011, "OUT_IN_PLAY": 0.438},
        "setup":  {"K": 0.28, "BB": 0.08, "HR": 0.028, "1B": 0.13, "2B": 0.04,  "3B": 0.004, "HBP": 0.011, "OUT_IN_PLAY": 0.427},
        "closer": {"K": 0.30, "BB": 0.07, "HR": 0.025, "1B": 0.13, "2B": 0.04,  "3B": 0.004, "HBP": 0.011, "OUT_IN_PLAY": 0.42},
    }


def test_inning_3_uses_starter() -> None:
    result = select_pitcher(3, 0, _starter(), _bullpen())
    assert result == _starter()


def test_inning_5_uses_starter() -> None:
    result = select_pitcher(5, 2, _starter(), _bullpen())
    assert result == _starter()


def test_inning_6_uses_middle() -> None:
    result = select_pitcher(6, 0, _starter(), _bullpen())
    assert result == _bullpen()["middle"]


def test_inning_8_close_game_uses_setup() -> None:
    result = select_pitcher(8, 2, _starter(), _bullpen())
    assert result == _bullpen()["setup"]


def test_inning_8_blowout_uses_middle() -> None:
    result = select_pitcher(8, 6, _starter(), _bullpen())
    assert result == _bullpen()["middle"]


def test_inning_9_save_situation_uses_closer() -> None:
    result = select_pitcher(9, 2, _starter(), _bullpen())  # home leads by 2
    assert result == _bullpen()["closer"]


def test_inning_9_tie_game_uses_setup() -> None:
    # Tie: not save situation. Use setup (or middle); accept either.
    result = select_pitcher(9, 0, _starter(), _bullpen())
    assert result in (_bullpen()["setup"], _bullpen()["middle"])


def test_inning_9_blowout_uses_middle() -> None:
    result = select_pitcher(9, 7, _starter(), _bullpen())
    assert result == _bullpen()["middle"]


def test_extra_innings_uses_closer_or_setup() -> None:
    # Inning 10+ in tied or close → setup; in blowout → middle.
    result = select_pitcher(10, 0, _starter(), _bullpen())
    assert result in (_bullpen()["setup"], _bullpen()["middle"], _bullpen()["closer"])
