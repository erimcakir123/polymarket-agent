"""Baseball inning guard testleri (SPEC-008)."""
from __future__ import annotations

from src.config.sport_rules import get_sport_rule


def test_mlb_comeback_thresholds_configured() -> None:
    thresholds = get_sport_rule("mlb", "comeback_thresholds")
    assert thresholds is not None
    assert thresholds[3] == 6   # inning 1-3: 6 run
    assert thresholds[5] == 5   # inning 4-5: 5 run
    assert thresholds[7] == 4   # inning 6-7: 4 run
    assert thresholds[8] == 3   # inning 8: 3 run
    assert thresholds[9] == 2   # inning 9: 2 run


def test_mlb_extra_inning_threshold_configured() -> None:
    assert get_sport_rule("mlb", "extra_inning_threshold") == 1
