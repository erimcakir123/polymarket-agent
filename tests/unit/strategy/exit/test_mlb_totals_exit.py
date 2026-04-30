import pytest
from src.strategy.exit.mlb_totals_exit import (
    MLBTotalsExitConfig,
    decide_mlb_totals_exit,
    ExitAction,
    ExitReason,
)


def _over_safe(i: int, t: int, o: int) -> tuple[float, str]:
    return (0.5, "fallback")


def _over_dead(i: int, t: int, o: int) -> tuple[float, str]:
    return (0.05, "table")


@pytest.fixture
def cfg():
    return MLBTotalsExitConfig(
        near_resolve_threshold=0.95, scale_out_threshold=0.85,
        structural_damage_ratio=0.30, predictive_safety_margin=0.04,
    )


def test_near_resolve_priority(cfg):
    d = decide_mlb_totals_exit(
        cfg=cfg, entry_price=0.5, current_bid=0.96, current_price=0.96,
        scaled_out_50=False, inning=5, outs=0, current_total=4,
        is_over_position=True, over_probability_fn=_over_safe,
    )
    assert d.action == ExitAction.SELL_ALL
    assert d.reason == ExitReason.NEAR_RESOLVE


def test_scale_out_priority(cfg):
    d = decide_mlb_totals_exit(
        cfg=cfg, entry_price=0.5, current_bid=0.86, current_price=0.86,
        scaled_out_50=False, inning=5, outs=0, current_total=4,
        is_over_position=True, over_probability_fn=_over_safe,
    )
    assert d.action == ExitAction.SELL_50


def test_predictive_dead_when_over_unlikely(cfg):
    """Late game, very low p_over -> PREDICTIVE_DEAD."""
    d = decide_mlb_totals_exit(
        cfg=cfg, entry_price=0.5, current_bid=0.20, current_price=0.20,
        scaled_out_50=False, inning=8, outs=2, current_total=3,
        is_over_position=True, over_probability_fn=_over_dead,
    )
    assert d.reason == ExitReason.PREDICTIVE_DEAD


def test_structural_damage(cfg):
    d = decide_mlb_totals_exit(
        cfg=cfg, entry_price=0.50, current_bid=0.10, current_price=0.10,
        scaled_out_50=False, inning=4, outs=0, current_total=3,
        is_over_position=True, over_probability_fn=_over_safe,
    )
    assert d.reason == ExitReason.STRUCTURAL_DAMAGE


def test_hold_default(cfg):
    d = decide_mlb_totals_exit(
        cfg=cfg, entry_price=0.50, current_bid=0.55, current_price=0.55,
        scaled_out_50=False, inning=3, outs=0, current_total=2,
        is_over_position=True, over_probability_fn=_over_safe,
    )
    assert d.action == ExitAction.HOLD


def test_no_m1_m2_m3_for_totals(cfg):
    """Totals exit must NOT trigger M1/M2/M3 even in late-game deficit-like states."""
    # State that would trigger M3 in score exit (inning 9 with low total) - Totals just HOLDs unless predictive triggers
    d = decide_mlb_totals_exit(
        cfg=cfg, entry_price=0.50, current_bid=0.55, current_price=0.55,
        scaled_out_50=False, inning=9, outs=2, current_total=6,
        is_over_position=True, over_probability_fn=_over_safe,
    )
    # _over_safe returns 0.5 -> not below bid+margin (0.55+0.04=0.59), no PREDICTIVE_DEAD
    # No M-rules -> HOLD
    assert d.action == ExitAction.HOLD
