# tests/unit/strategy/exit/test_mlb_score_exit.py
import pytest
from src.strategy.exit.mlb_score_exit import (
    MLBExitConfig,
    decide_mlb_score_exit,
    ExitAction,
    ExitReason,
)


def _wp_safe(p: int, v: int, s: int) -> tuple[float, str]:
    return (0.5, "fallback")


def _wp_dead(p: int, v: int, s: int) -> tuple[float, str]:
    return (0.05, "table")


@pytest.fixture
def cfg():
    return MLBExitConfig(
        near_resolve_threshold=0.95, scale_out_threshold=0.85,
        structural_damage_ratio=0.30, predictive_safety_margin=0.04,
    )


def test_near_resolve_priority(cfg):
    d = decide_mlb_score_exit(
        cfg=cfg, entry_price=0.5, current_bid=0.96, current_price=0.96,
        scaled_out_50=False, inning=5, outs=0, base_state=0,
        run_diff=0, is_home_position=True, win_probability_fn=_wp_safe,
    )
    assert d.action == ExitAction.SELL_ALL
    assert d.reason == ExitReason.NEAR_RESOLVE


def test_scale_out_priority(cfg):
    d = decide_mlb_score_exit(
        cfg=cfg, entry_price=0.5, current_bid=0.86, current_price=0.86,
        scaled_out_50=False, inning=5, outs=0, base_state=0,
        run_diff=0, is_home_position=True, win_probability_fn=_wp_safe,
    )
    assert d.action == ExitAction.SELL_50
    assert d.reason == ExitReason.SCALE_OUT


def test_scale_out_skipped_if_already_scaled(cfg):
    """SCALE_OUT one-shot only."""
    d = decide_mlb_score_exit(
        cfg=cfg, entry_price=0.5, current_bid=0.86, current_price=0.86,
        scaled_out_50=True, inning=5, outs=0, base_state=0,
        run_diff=0, is_home_position=True, win_probability_fn=_wp_safe,
    )
    assert d.action != ExitAction.SELL_50


def test_m1_inning_7_deficit_5(cfg):
    d = decide_mlb_score_exit(
        cfg=cfg, entry_price=0.5, current_bid=0.20, current_price=0.20,
        scaled_out_50=False, inning=7, outs=0, base_state=0,
        run_diff=+5, is_home_position=False,
        win_probability_fn=_wp_safe,
    )
    assert d.action == ExitAction.SELL_ALL
    assert d.reason == ExitReason.M1_SEVENTH_DEFICIT_5


def test_m2_inning_8_deficit_3(cfg):
    d = decide_mlb_score_exit(
        cfg=cfg, entry_price=0.5, current_bid=0.30, current_price=0.30,
        scaled_out_50=False, inning=8, outs=1, base_state=0,
        run_diff=+3, is_home_position=False, win_probability_fn=_wp_safe,
    )
    assert d.reason == ExitReason.M2_EIGHTH_DEFICIT_3


def test_m3_inning_9_deficit_1(cfg):
    d = decide_mlb_score_exit(
        cfg=cfg, entry_price=0.5, current_bid=0.10, current_price=0.10,
        scaled_out_50=False, inning=9, outs=2, base_state=0,
        run_diff=+1, is_home_position=False, win_probability_fn=_wp_safe,
    )
    assert d.reason == ExitReason.M3_NINTH_DEFICIT_1


def test_predictive_dead_when_we_below_bid(cfg):
    """Late-game with WE 0.05 well below bid 0.20 → PREDICTIVE_DEAD."""
    d = decide_mlb_score_exit(
        cfg=cfg, entry_price=0.5, current_bid=0.20, current_price=0.20,
        scaled_out_50=False, inning=8, outs=2, base_state=0,
        run_diff=-1, is_home_position=True, win_probability_fn=_wp_dead,
    )
    assert d.reason == ExitReason.PREDICTIVE_DEAD


def test_structural_damage(cfg):
    d = decide_mlb_score_exit(
        cfg=cfg, entry_price=0.50, current_bid=0.10, current_price=0.10,
        scaled_out_50=False, inning=4, outs=0, base_state=0,
        run_diff=0, is_home_position=True, win_probability_fn=_wp_safe,
    )
    assert d.reason == ExitReason.STRUCTURAL_DAMAGE


def test_hold_default(cfg):
    d = decide_mlb_score_exit(
        cfg=cfg, entry_price=0.50, current_bid=0.55, current_price=0.55,
        scaled_out_50=False, inning=3, outs=0, base_state=0,
        run_diff=0, is_home_position=True, win_probability_fn=_wp_safe,
    )
    assert d.action == ExitAction.HOLD
