"""is_mathematically_dead() unit testleri."""
from __future__ import annotations

import pytest
from src.domain.math.safe_lead import is_mathematically_dead

_M = 0.861  # NBA default multiplier


def test_dead_17_pts_240s():
    # 0.861 * sqrt(240) = 13.33 → 17 >= 13.33 → True
    assert is_mathematically_dead(deficit=17, clock_seconds=240, multiplier=_M) is True


def test_dead_13_pts_120s():
    # 0.861 * sqrt(120) = 9.43 → 13 >= 9.43 → True
    assert is_mathematically_dead(deficit=13, clock_seconds=120, multiplier=_M) is True


def test_dead_8_pts_45s():
    # 0.861 * sqrt(45) = 5.77 → 8 >= 5.77 → True
    assert is_mathematically_dead(deficit=8, clock_seconds=45, multiplier=_M) is True


def test_dead_25_pts_420s():
    # 0.861 * sqrt(420) = 17.64 → 25 >= 17.64 → True
    assert is_mathematically_dead(deficit=25, clock_seconds=420, multiplier=_M) is True


def test_alive_5_pts_240s():
    # 0.861 * sqrt(240) = 13.33 → 5 < 13.33 → False
    assert is_mathematically_dead(deficit=5, clock_seconds=240, multiplier=_M) is False


def test_zero_seconds_positive_deficit():
    # clock = 0, deficit > 0 → oyun bitti, gerideyiz → True
    assert is_mathematically_dead(deficit=1, clock_seconds=0, multiplier=_M) is True


def test_negative_deficit_is_alive():
    # Negatif deficit = biz öndeyiz → False
    assert is_mathematically_dead(deficit=-5, clock_seconds=120, multiplier=_M) is False
