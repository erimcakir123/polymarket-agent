import pytest
from src.strategy.exit.mlb_run_line_exit import (
    MLBRunLineExitConfig,
    decide_mlb_run_line_exit,
    ExitAction,
    ExitReason,
)


def _cover_safe(p: int, v: int, s: int) -> tuple[float, str]:
    return (0.5, "fallback")


def _cover_dead(p: int, v: int, s: int) -> tuple[float, str]:
    return (0.05, "table")


@pytest.fixture
def cfg():
    return MLBRunLineExitConfig(
        near_resolve_threshold=0.95, scale_out_threshold=0.85,
        structural_damage_ratio=0.30, predictive_safety_margin=0.04,
    )


def test_near_resolve_priority(cfg):
    d = decide_mlb_run_line_exit(
        cfg=cfg, entry_price=0.5, current_bid=0.96, current_price=0.96,
        scaled_out_50=False, inning=5, outs=0, base_state=0,
        run_diff=0, is_home_position=True,
        cover_probability_fn=_cover_safe,
    )
    assert d.action == ExitAction.SELL_ALL
    assert d.reason == ExitReason.NEAR_RESOLVE


def test_scale_out_priority(cfg):
    d = decide_mlb_run_line_exit(
        cfg=cfg, entry_price=0.5, current_bid=0.86, current_price=0.86,
        scaled_out_50=False, inning=5, outs=0, base_state=0,
        run_diff=0, is_home_position=True,
        cover_probability_fn=_cover_safe,
    )
    assert d.action == ExitAction.SELL_50


def test_m1_inning_7_deficit_5(cfg):
    d = decide_mlb_run_line_exit(
        cfg=cfg, entry_price=0.5, current_bid=0.20, current_price=0.20,
        scaled_out_50=False, inning=7, outs=0, base_state=0,
        run_diff=+5, is_home_position=False,
        cover_probability_fn=_cover_safe,
    )
    assert d.action == ExitAction.SELL_ALL
    assert d.reason == ExitReason.M1_SEVENTH_DEFICIT_5


def test_predictive_dead_when_p_cover_below_bid(cfg):
    d = decide_mlb_run_line_exit(
        cfg=cfg, entry_price=0.5, current_bid=0.20, current_price=0.20,
        scaled_out_50=False, inning=8, outs=2, base_state=0,
        run_diff=-1, is_home_position=True,
        cover_probability_fn=_cover_dead,
    )
    assert d.reason == ExitReason.PREDICTIVE_DEAD


def test_structural_damage(cfg):
    d = decide_mlb_run_line_exit(
        cfg=cfg, entry_price=0.50, current_bid=0.10, current_price=0.10,
        scaled_out_50=False, inning=4, outs=0, base_state=0,
        run_diff=0, is_home_position=True,
        cover_probability_fn=_cover_safe,
    )
    assert d.reason == ExitReason.STRUCTURAL_DAMAGE


def test_hold_default(cfg):
    d = decide_mlb_run_line_exit(
        cfg=cfg, entry_price=0.50, current_bid=0.55, current_price=0.55,
        scaled_out_50=False, inning=3, outs=0, base_state=0,
        run_diff=0, is_home_position=True,
        cover_probability_fn=_cover_safe,
    )
    assert d.action == ExitAction.HOLD
