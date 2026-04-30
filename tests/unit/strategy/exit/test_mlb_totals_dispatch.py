"""Unit tests for _mlb_totals_dispatch.py — MLB totals exit dispatcher."""
from types import SimpleNamespace

import pytest

from src.models.enums import ExitReason
from src.strategy.exit._mlb_totals_dispatch import check_mlb_totals_exit
from src.strategy.exit.mlb_totals_exit import MLBTotalsExitConfig


@pytest.fixture
def cfg():
    return MLBTotalsExitConfig(
        near_resolve_threshold=0.95,
        scale_out_threshold=0.85,
        structural_damage_ratio=0.30,
        predictive_safety_margin=0.04,
    )


def _pos(**kwargs):
    defaults = dict(
        entry_price=0.5, bid_price=0.5, current_price=0.5, scaled_out_50=False
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_invalid_inning_returns_none(cfg):
    """No inning info → None."""
    score = {"home_score": 3, "away_score": 4}
    assert check_mlb_totals_exit(_pos(), score, cfg, over_under_line=8.5) is None


def test_missing_score_returns_none(cfg):
    """Missing score values → None."""
    score = {"period_number": 5, "home_score": None, "away_score": None}
    assert check_mlb_totals_exit(_pos(), score, cfg, over_under_line=8.5) is None


def test_near_resolve_routes(cfg):
    """High bid → near-resolve signal."""
    score = {"period_number": 7, "outs": 0, "home_score": 5, "away_score": 4}
    sig = check_mlb_totals_exit(_pos(bid_price=0.96), score, cfg, over_under_line=8.5)
    assert sig is not None
    assert sig.reason == ExitReason.MLB_TOTALS_NEAR_RESOLVE
    assert sig.partial is False
    assert sig.sell_pct == 1.00


def test_predictive_dead_via_low_projected_total(cfg):
    """Very low projected total (low-scoring game, UNDER position) → predictive dead.

    Scenario: inning 6, total=2, line=8.5, over_position=False (we backed UNDER).
    Projected final = 2 * (9/6) = 3.0 — well below 8.5 - 1 = 7.5 → p_over=0.15
    p_position for UNDER = 1 - 0.15 = 0.85 → above threshold (bid=0.10), HOLD.
    Actually UNDER wins here so not predictive_dead. Use OVER position with high bid
    and very low projected to trigger dead.
    """
    # OVER position, projected very low → p_over=0.15, bid=0.50, margin=0.04
    # p_position = 0.15, bid=0.50 → 0.15 < 0.50 + 0.04 → PREDICTIVE_DEAD fires
    score = {
        "period_number": 6,
        "outs": 0,
        "home_score": 1,
        "away_score": 1,
        "is_over_position": True,
    }
    sig = check_mlb_totals_exit(_pos(bid_price=0.50), score, cfg, over_under_line=8.5)
    assert sig is not None
    assert sig.reason == ExitReason.MLB_TOTALS_PREDICTIVE_DEAD


def test_hold_early_game(cfg):
    """Early innings, ambiguous total → None (HOLD, fallback 0.5)."""
    score = {
        "period_number": 3,
        "outs": 0,
        "home_score": 3,
        "away_score": 3,
        "is_over_position": True,
    }
    sig = check_mlb_totals_exit(_pos(bid_price=0.50), score, cfg, over_under_line=8.5)
    # projected = 6 * (9/3) = 18 → p_over=0.85 but source is "table" only if != 0.5
    # 0.85 != 0.5 → "table", p_position=0.85 which is NOT < bid(0.50)+margin(0.04)
    assert sig is None


def test_inning_key_fallback(cfg):
    """Uses 'inning' key when 'period_number' absent."""
    score = {"inning": 7, "outs": 0, "home_score": 5, "away_score": 4}
    sig = check_mlb_totals_exit(_pos(bid_price=0.96), score, cfg, over_under_line=8.5)
    assert sig is not None
    assert sig.reason == ExitReason.MLB_TOTALS_NEAR_RESOLVE
