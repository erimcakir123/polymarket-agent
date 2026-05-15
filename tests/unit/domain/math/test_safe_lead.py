"""safe_lead.py için birim testler — Bill James %99 + EV-bazlı predictive."""
from __future__ import annotations

import pytest

from src.domain.math.safe_lead import (
    estimate_comeback_rate_ml,
    estimate_comeback_rate_totals,
    is_total_dead,
    predictive_exit_decision_totals,
)


# ── is_total_dead ─────────────────────────────────────────────────────────────


def test_is_total_dead_invalid_side_raises() -> None:
    with pytest.raises(ValueError):
        is_total_dead(220.0, 200, 100, "wrong")


def test_is_total_dead_over_seconds_zero_target_not_reached_dead() -> None:
    """Süre bitti, hedefe ulaşılamadı → over ölü."""
    assert is_total_dead(220.0, 210, 0, "over") is True
    assert is_total_dead(220.0, 220, 0, "over") is False


def test_is_total_dead_under_seconds_zero_target_passed_dead() -> None:
    """Süre bitti, hedef aşıldı → under ölü."""
    assert is_total_dead(220.0, 225, 0, "under") is True
    assert is_total_dead(220.0, 215, 0, "under") is False


def test_is_total_dead_over_threshold_check() -> None:
    """1.218 × √100 = 12.18 — points_needed 15 > 12.18 → over ölü."""
    assert is_total_dead(220.0, 205, 100, "over", 1.218) is True
    assert is_total_dead(220.0, 210, 100, "over", 1.218) is False


# ── estimate_comeback_rate_ml ────────────────────────────────────────────────


def test_estimate_comeback_rate_ml_no_deficit_full_rate() -> None:
    assert estimate_comeback_rate_ml(0, 100) == 1.0
    assert estimate_comeback_rate_ml(-5, 100) == 1.0


def test_estimate_comeback_rate_ml_seconds_zero_lost() -> None:
    assert estimate_comeback_rate_ml(5, 0) == 0.0
    assert estimate_comeback_rate_ml(0, 0) == 1.0


def test_estimate_comeback_rate_ml_monotonic_in_seconds() -> None:
    """Aynı deficit, daha fazla süre → daha yüksek comeback şansı."""
    short = estimate_comeback_rate_ml(5, 60)
    long = estimate_comeback_rate_ml(5, 600)
    assert long > short
    assert 0.0 <= short <= 1.0
    assert 0.0 <= long <= 1.0


# ── estimate_comeback_rate_totals ────────────────────────────────────────────


def test_estimate_comeback_rate_totals_invalid_side_raises() -> None:
    with pytest.raises(ValueError):
        estimate_comeback_rate_totals(5.0, 100, "wrong")


def test_estimate_comeback_rate_totals_target_passed_over_wins() -> None:
    """points_diff ≤ 0 → hedef aşıldı; over kazandı (1.0), under kaybetti (0.0)."""
    assert estimate_comeback_rate_totals(0.0, 100, "over") == 1.0
    assert estimate_comeback_rate_totals(-3.0, 100, "over") == 1.0
    assert estimate_comeback_rate_totals(0.0, 100, "under") == 0.0
    assert estimate_comeback_rate_totals(-3.0, 100, "under") == 0.0


def test_estimate_comeback_rate_totals_seconds_zero_under_wins() -> None:
    """Süre bitti, hedef aşılmamış → over kaybetti, under kazandı."""
    assert estimate_comeback_rate_totals(5.0, 0, "over") == 0.0
    assert estimate_comeback_rate_totals(5.0, 0, "under") == 1.0


def test_estimate_comeback_rate_totals_over_under_complement() -> None:
    """Aynı points_diff + seconds için over + under ≈ 1.0 (CDF tamamlayıcısı)."""
    over = estimate_comeback_rate_totals(8.0, 200, "over")
    under = estimate_comeback_rate_totals(8.0, 200, "under")
    assert abs(over + under - 1.0) < 1e-9


# ── predictive_exit_decision_totals ──────────────────────────────────────────


def test_predictive_exit_decision_totals_invalid_side_raises() -> None:
    with pytest.raises(ValueError):
        predictive_exit_decision_totals(220.0, 200, 100, "x", current_bid=0.10)


def test_predictive_exit_decision_totals_seconds_zero_over_under_target_exits() -> None:
    """Süre bitti, current < target → over kaybetti (EXIT)."""
    assert (
        predictive_exit_decision_totals(220.0, 210, 0, "over", current_bid=0.10)
        is True
    )
    assert (
        predictive_exit_decision_totals(220.0, 225, 0, "over", current_bid=0.10)
        is False
    )


def test_predictive_exit_decision_totals_target_passed_under_exits() -> None:
    """points_until_decision ≤ 0 → under kaybetti, over hold."""
    assert (
        predictive_exit_decision_totals(200.0, 200, 100, "under", current_bid=0.10)
        is True
    )
    assert (
        predictive_exit_decision_totals(200.0, 200, 100, "over", current_bid=0.10)
        is False
    )
