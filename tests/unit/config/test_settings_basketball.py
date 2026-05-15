"""BasketballExitConfig + nested sub-models için birim testler (SPEC-J)."""
from __future__ import annotations

from src.config.settings import (
    AppConfig,
    BasketballExitConfig,
    OvertimeExitConfig,
    PredictiveExitConfig,
    TotalsEmpiricalConfig,
)


def test_app_config_has_exit_basketball_default() -> None:
    cfg = AppConfig()
    assert isinstance(cfg.exit_basketball, BasketballExitConfig)


def test_basketball_exit_config_top_level_defaults() -> None:
    bk = BasketballExitConfig()
    assert bk.structural_damage_ratio == 0.30
    assert bk.totals_multiplier == 1.218


def test_basketball_exit_config_nested_overtime_defaults() -> None:
    ot = BasketballExitConfig().overtime
    assert isinstance(ot, OvertimeExitConfig)
    assert ot.seconds == 60
    assert ot.deficit == 8


def test_basketball_exit_config_nested_totals_empirical_defaults() -> None:
    tot = BasketballExitConfig().totals_empirical
    assert isinstance(tot, TotalsEmpiricalConfig)
    assert tot.ot_over_scale_pct == 0.5
    assert tot.q4_late_seconds == 360
    assert tot.q4_late_gap == 7
    assert tot.q4_final_seconds == 180
    assert tot.q4_final_gap == 4
    assert tot.q4_endgame_seconds == 60
    assert tot.q4_endgame_gap == 3


def test_basketball_exit_config_nested_predictive_defaults() -> None:
    pe = BasketballExitConfig().predictive_exit
    assert isinstance(pe, PredictiveExitConfig)
    assert pe.enabled is True
    assert pe.safety_margin == 0.03
    assert pe.hold_threshold == 0.20


def test_basketball_exit_config_factory_independence() -> None:
    """default_factory ile her instance bağımsız nested model alır."""
    a = BasketballExitConfig()
    b = BasketballExitConfig()
    assert a.totals_empirical is not b.totals_empirical
    assert a.predictive_exit is not b.predictive_exit
    assert a.overtime is not b.overtime
