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


# ── estimate_comeback_rate_ml ─────────────────────────────────────────────────
from src.domain.math.safe_lead import (
    estimate_comeback_rate_ml,
    estimate_comeback_rate_spread,
    estimate_comeback_rate_totals,
    predictive_exit_decision_ml,
    predictive_exit_decision_spread,
    predictive_exit_decision_totals,
)


def test_comeback_ml_large_deficit_high_z_very_low_rate():
    # z = 20 / (0.3727 × √720) ≈ 2.0 → rate ≈ 0.0228
    rate = estimate_comeback_rate_ml(20, 720)
    assert abs(rate - 0.0228) < 0.001


def test_comeback_ml_moderate_deficit_rate_above_threshold():
    # z = 8 / (0.3727 × √720) ≈ 0.8 → rate ≈ 0.212
    rate = estimate_comeback_rate_ml(8, 720)
    assert abs(rate - 0.212) < 0.005


def test_comeback_ml_deficit_12_seconds_180():
    # z = 12 / (0.3727 × √180) ≈ 2.4 → rate ≈ 0.0082
    rate = estimate_comeback_rate_ml(12, 180)
    assert abs(rate - 0.0082) < 0.001


def test_comeback_ml_zero_deficit_returns_one():
    assert estimate_comeback_rate_ml(0, 60) == 1.0


def test_comeback_ml_negative_deficit_returns_one():
    assert estimate_comeback_rate_ml(-5, 120) == 1.0


def test_comeback_ml_zero_seconds_positive_deficit_returns_zero():
    assert estimate_comeback_rate_ml(5, 0) == 0.0


def test_comeback_ml_zero_seconds_zero_deficit_returns_one():
    assert estimate_comeback_rate_ml(0, 0) == 1.0


def test_comeback_ml_clamp_min_zero():
    # Çok büyük z → rate çok küçük ama >= 0
    rate = estimate_comeback_rate_ml(100, 10)
    assert 0.0 <= rate <= 1.0


# ── estimate_comeback_rate_spread ─────────────────────────────────────────────

def test_comeback_spread_zero_margin_returns_one():
    assert estimate_comeback_rate_spread(0.0, 120) == 1.0


def test_comeback_spread_negative_margin_returns_one():
    assert estimate_comeback_rate_spread(-3.0, 120) == 1.0


def test_comeback_spread_delegates_to_ml():
    # margin_to_cover=10 → int(round(10)) = 10 → same as ml
    rate_spread = estimate_comeback_rate_spread(10.0, 300)
    rate_ml = estimate_comeback_rate_ml(10, 300)
    assert abs(rate_spread - rate_ml) < 1e-9


def test_comeback_spread_rounds_fractional_margin():
    # 7.5 → rounds to 8
    rate = estimate_comeback_rate_spread(7.5, 300)
    rate_ml_8 = estimate_comeback_rate_ml(8, 300)
    assert abs(rate - rate_ml_8) < 1e-9


# ── estimate_comeback_rate_totals ─────────────────────────────────────────────

def test_comeback_totals_invalid_side_raises():
    with pytest.raises(ValueError, match="side"):
        estimate_comeback_rate_totals(10.0, 60, "both")


def test_comeback_totals_zero_seconds_over_returns_zero():
    # seconds=0, points_diff>0: süre doldu, over hedefine ulaşamadı → kaybetti
    assert estimate_comeback_rate_totals(5.0, 0, "over") == 0.0


def test_comeback_totals_zero_seconds_under_returns_one():
    # seconds=0, points_diff>0: süre doldu, under hedefi aşılmadı → kazandı
    assert estimate_comeback_rate_totals(5.0, 0, "under") == 1.0


def test_comeback_totals_zero_diff_over_returns_one():
    # points_diff=0: current=target → over tam ulaştı → kazandı
    assert estimate_comeback_rate_totals(0.0, 120, "over") == 1.0


def test_comeback_totals_zero_diff_under_returns_zero():
    # points_diff=0: current=target → under tam sınırda, herhangi bir puan kaybettirir → 0
    assert estimate_comeback_rate_totals(0.0, 120, "under") == 0.0


def test_comeback_totals_negative_diff_returns_one():
    assert estimate_comeback_rate_totals(-5.0, 120, "over") == 1.0


def test_comeback_totals_over_large_gap_low_rate():
    # points_diff=25, seconds=120, z=25/(0.5270*√120)≈4.33 → rate very small
    rate = estimate_comeback_rate_totals(25.0, 120, "over")
    assert rate < 0.01


def test_comeback_totals_under_rate_high_when_large_gap():
    # Under side: large excess → likely to stay under → high rate
    rate = estimate_comeback_rate_totals(25.0, 120, "under")
    assert rate > 0.99


# ── predictive_exit_decision_ml ───────────────────────────────────────────────

def test_predictive_ml_high_comeback_holds():
    # deficit=8, seconds=720: comeback≈0.212 ≥ hold_threshold=0.20 → HOLD
    result = predictive_exit_decision_ml(deficit=8, seconds=720, current_bid=0.30)
    assert result is False


def test_predictive_ml_low_comeback_bid_beats_ev_exits():
    # deficit=12, seconds=180: comeback≈0.008, bid+0.03=0.13>0.008 → EXIT
    result = predictive_exit_decision_ml(deficit=12, seconds=180, current_bid=0.10)
    assert result is True


def test_predictive_ml_key_scenario_math_dead_not_yet():
    # deficit=10, seconds=180: math_dead eşiği=0.861×√180=11.55>10 → math_dead değil
    # ama predictive: comeback≈0.023, bid+0.03=0.18>0.023 → EXIT
    # Kilit senaryo: predictive math_dead'den önce yakaladı
    result = predictive_exit_decision_ml(deficit=10, seconds=180, current_bid=0.15)
    assert result is True


def test_predictive_ml_high_comeback_holds_2():
    # deficit=5, seconds=300: z≈0.775, comeback≈0.22 ≥ 0.20 → HOLD
    result = predictive_exit_decision_ml(deficit=5, seconds=300, current_bid=0.30)
    assert result is False


def test_predictive_ml_zero_deficit_never_exits():
    result = predictive_exit_decision_ml(deficit=0, seconds=120, current_bid=0.50)
    assert result is False


def test_predictive_ml_zero_seconds_positive_deficit_exits():
    result = predictive_exit_decision_ml(deficit=1, seconds=0, current_bid=0.50)
    assert result is True


def test_predictive_ml_zero_seconds_zero_deficit_holds():
    result = predictive_exit_decision_ml(deficit=0, seconds=0, current_bid=0.50)
    assert result is False


def test_predictive_ml_low_bid_but_holds_when_comeback_high():
    # comeback >= hold_threshold → HOLD even if bid is very low
    result = predictive_exit_decision_ml(deficit=8, seconds=720, current_bid=0.01)
    assert result is False


# ── predictive_exit_decision_spread ───────────────────────────────────────────

def test_predictive_spread_zero_margin_holds():
    result = predictive_exit_decision_spread(margin_to_cover=0.0, seconds=120, current_bid=0.50)
    assert result is False


def test_predictive_spread_zero_seconds_positive_margin_exits():
    result = predictive_exit_decision_spread(margin_to_cover=3.0, seconds=0, current_bid=0.50)
    assert result is True


def test_predictive_spread_high_comeback_holds():
    # margin=5, seconds=720: comeback close to ml(5,720)≈0.36 → HOLD
    result = predictive_exit_decision_spread(margin_to_cover=5.0, seconds=720, current_bid=0.30)
    assert result is False


def test_predictive_spread_low_comeback_exits():
    # margin=15, seconds=180: comeback very low → EXIT
    result = predictive_exit_decision_spread(margin_to_cover=15.0, seconds=180, current_bid=0.10)
    assert result is True


# ── predictive_exit_decision_totals ───────────────────────────────────────────

def test_predictive_totals_invalid_side_raises():
    with pytest.raises(ValueError, match="side"):
        predictive_exit_decision_totals(220.0, 200, 120, "both", 0.10)


def test_predictive_totals_over_zero_seconds_exits_when_short():
    # seconds=0, current=210<target=220 → EXIT
    result = predictive_exit_decision_totals(220.0, 210, 0, "over", 0.10)
    assert result is True


def test_predictive_totals_over_zero_seconds_holds_when_reached():
    # seconds=0, current=220>=target=220 → HOLD (already over)
    result = predictive_exit_decision_totals(220.0, 220, 0, "over", 0.10)
    assert result is False


def test_predictive_totals_under_zero_seconds_exits_when_exceeded():
    # seconds=0, current=225>=target=220 → EXIT (under blown)
    result = predictive_exit_decision_totals(220.0, 225, 0, "under", 0.10)
    assert result is True


def test_predictive_totals_under_zero_seconds_holds_when_safe():
    # seconds=0, current=215<target=220 → HOLD (under safe)
    result = predictive_exit_decision_totals(220.0, 215, 0, "under", 0.10)
    assert result is False


def test_predictive_totals_over_already_reached_holds():
    # points_diff=220-225=-5 ≤ 0 → HOLD
    result = predictive_exit_decision_totals(220.0, 225, 120, "over", 0.10)
    assert result is False


def test_predictive_totals_under_already_exceeded_exits():
    # current=225 > target=220 → points_until_decision=-5 ≤ 0 → under kaybetti → EXIT
    result = predictive_exit_decision_totals(220.0, 225, 60, "under", 0.10)
    assert result is True


def test_predictive_totals_over_large_gap_low_comeback_exits():
    # target=240, current=200, seconds=120 → gap=40, huge z, comeback≈0
    result = predictive_exit_decision_totals(240.0, 200, 120, "over", 0.10)
    assert result is True
