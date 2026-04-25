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


# ── is_spread_dead ────────────────────────────────────────────────
from src.domain.math.safe_lead import is_spread_dead, is_total_dead

_SM = 0.861   # spread multiplier (moneyline ile aynı)
_TM = 1.218   # total multiplier (0.861 × sqrt(2))


def test_spread_dead_8pts_60s():
    # 0.861 * sqrt(60) = 6.67 → 8 >= 6.67 → True
    assert is_spread_dead(margin_to_cover=8.0, seconds_remaining=60, multiplier=_SM) is True


def test_spread_alive_8pts_240s():
    # 0.861 * sqrt(240) = 13.33 → 8 < 13.33 → False
    assert is_spread_dead(margin_to_cover=8.0, seconds_remaining=240, multiplier=_SM) is False


def test_spread_dead_5pts_30s():
    # 0.861 * sqrt(30) = 4.71 → 5 >= 4.71 → True
    assert is_spread_dead(margin_to_cover=5.0, seconds_remaining=30, multiplier=_SM) is True


def test_spread_zero_margin_alive():
    # Margin ≤ 0 → zaten cover'dayız → False
    assert is_spread_dead(margin_to_cover=0.0, seconds_remaining=60, multiplier=_SM) is False


def test_spread_negative_margin_alive():
    assert is_spread_dead(margin_to_cover=-3.0, seconds_remaining=120, multiplier=_SM) is False


def test_spread_zero_seconds_positive_margin():
    # Oyun bitti, gerideyiz → True
    assert is_spread_dead(margin_to_cover=1.0, seconds_remaining=0, multiplier=_SM) is True


def test_spread_zero_seconds_zero_margin():
    # Small positive → covering required strictly → True
    assert is_spread_dead(margin_to_cover=0.1, seconds_remaining=0, multiplier=_SM) is True


# ── is_total_dead ─────────────────────────────────────────────────
def test_total_dead_over_not_enough_pace():
    # target=220, current=200, 240s, "over"
    # points_needed=20, threshold=1.218*sqrt(240)=18.87 → 20>18.87 → True
    assert is_total_dead(
        target_total=220.0, current_total=200, seconds_remaining=240, side="over", multiplier=_TM,
    ) is True


def test_total_alive_over_reachable():
    # target=220, current=210, 360s, "over"
    # points_needed=10, threshold=1.218*sqrt(360)=23.1 → 10<23.1 → False
    assert is_total_dead(
        target_total=220.0, current_total=210, seconds_remaining=360, side="over", multiplier=_TM,
    ) is False


def test_total_dead_under_exceeded():
    # target=220, current=245, 60s, "under"
    # points_needed=220-245=-25 → -(-25)=25>threshold(9.42) → True
    assert is_total_dead(
        target_total=220.0, current_total=245, seconds_remaining=60, side="under", multiplier=_TM,
    ) is True


def test_total_alive_under_not_exceeded():
    # target=220, current=230, 240s, "under"
    # points_needed=-10 → -(-10)=10 < threshold(18.87) → False
    assert is_total_dead(
        target_total=220.0, current_total=230, seconds_remaining=240, side="under", multiplier=_TM,
    ) is False


def test_total_dead_over_zero_seconds():
    # Oyun bitti, total ulaşılamadı
    assert is_total_dead(
        target_total=220.0, current_total=215, seconds_remaining=0, side="over", multiplier=_TM,
    ) is True


def test_total_dead_under_zero_seconds_exceeded():
    assert is_total_dead(
        target_total=220.0, current_total=225, seconds_remaining=0, side="under", multiplier=_TM,
    ) is True


def test_total_alive_over_zero_seconds_reached():
    # current >= target → over kazandı → NOT dead
    assert is_total_dead(
        target_total=220.0, current_total=221, seconds_remaining=0, side="over", multiplier=_TM,
    ) is False


def test_total_invalid_side_raises():
    import pytest
    with pytest.raises(ValueError, match="side"):
        is_total_dead(220.0, 200, 120, "both", _TM)
