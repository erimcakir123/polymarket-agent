"""Tests for ScratchDetector — lineup change detection.

SPEC-R Plan 3 T5.
"""
import pytest
from unittest.mock import MagicMock
from src.infrastructure.mlb_data.scratch_detector import ScratchDetector


def test_identical_lineups_no_diff() -> None:
    detector = ScratchDetector(MagicMock())
    lineup = {"home": [1, 2, 3, 4, 5, 6, 7, 8, 9],
              "away": [10, 11, 12, 13, 14, 15, 16, 17, 18]}
    result = ScratchDetector.diff(lineup, lineup)
    assert result == {"home": [], "away": []}


def test_one_home_swap() -> None:
    prev = {"home": [1, 2, 3, 4, 5, 6, 7, 8, 9], "away": [10] * 9}
    curr = {"home": [1, 99, 3, 4, 5, 6, 7, 8, 9], "away": [10] * 9}
    result = ScratchDetector.diff(prev, curr)
    assert result["home"] == [(2, 99)]
    assert result["away"] == []


def test_multiple_swaps() -> None:
    prev = {"home": [1, 2, 3, 4, 5, 6, 7, 8, 9], "away": [10] * 9}
    curr = {"home": [1, 99, 3, 88, 5, 6, 7, 8, 9], "away": [10] * 9}
    result = ScratchDetector.diff(prev, curr)
    assert result["home"] == [(2, 99), (4, 88)]


def test_both_teams_have_swaps() -> None:
    prev = {"home": [1, 2, 3, 4, 5, 6, 7, 8, 9],
            "away": [10, 11, 12, 13, 14, 15, 16, 17, 18]}
    curr = {"home": [1, 2, 3, 4, 5, 6, 7, 8, 99],
            "away": [10, 11, 88, 13, 14, 15, 16, 17, 18]}
    result = ScratchDetector.diff(prev, curr)
    assert result["home"] == [(9, 99)]
    assert result["away"] == [(12, 88)]


def test_unequal_lengths_raises() -> None:
    prev = {"home": [1, 2, 3], "away": [10] * 9}
    curr = {"home": [1, 2, 3, 4], "away": [10] * 9}
    with pytest.raises(ValueError):
        ScratchDetector.diff(prev, curr)


def test_get_current_lineup_calls_statsapi() -> None:
    fake_api = MagicMock()
    fake_api.get_lineup.return_value = {"home": [1, 2], "away": [3, 4]}
    detector = ScratchDetector(fake_api)
    result = detector.get_current_lineup(12345)
    fake_api.get_lineup.assert_called_once_with(12345)
    assert result == {"home": [1, 2], "away": [3, 4]}
