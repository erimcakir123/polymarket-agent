"""Unit tests for _mlb_exit_dispatch.py — MLB moneyline exit dispatcher."""
from types import SimpleNamespace

import pytest

from src.models.enums import ExitReason
from src.strategy.exit._mlb_exit_dispatch import check_mlb_score_exit
from src.strategy.exit.mlb_score_exit import MLBExitConfig


@pytest.fixture
def cfg():
    return MLBExitConfig(
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
    score = {"home_score": 2, "away_score": 1}
    assert check_mlb_score_exit(_pos(), score, cfg) is None


def test_missing_score_returns_none(cfg):
    """Missing score values → None."""
    score = {"period_number": 5, "home_score": None, "away_score": None}
    assert check_mlb_score_exit(_pos(), score, cfg) is None


def test_inning_zero_returns_none(cfg):
    """period_number=0 is invalid → None."""
    score = {"period_number": 0, "home_score": 3, "away_score": 1}
    assert check_mlb_score_exit(_pos(), score, cfg) is None


def test_near_resolve_routes(cfg):
    """High bid price → near-resolve signal."""
    score = {"period_number": 5, "outs": 0, "home_score": 5, "away_score": 2}
    sig = check_mlb_score_exit(_pos(bid_price=0.96), score, cfg)
    assert sig is not None
    assert sig.reason == ExitReason.MLB_NEAR_RESOLVE
    assert sig.partial is False
    assert sig.sell_pct == 1.00


def test_m3_late_game(cfg):
    """Inning 9, deficit 1 (we backed away team, home leads by 1) → M3 fire."""
    score = {
        "period_number": 9,
        "outs": 2,
        "home_score": 4,
        "away_score": 3,
        "is_home_position": False,
    }
    sig = check_mlb_score_exit(_pos(bid_price=0.10), score, cfg)
    assert sig is not None
    assert sig.reason == ExitReason.MLB_M3_NINTH_DEFICIT_1


def test_m1_seventh_deficit_five(cfg):
    """Inning 7, deficit 5 → M1 fire."""
    score = {
        "period_number": 7,
        "outs": 0,
        "home_score": 2,
        "away_score": 7,
        "is_home_position": True,
    }
    sig = check_mlb_score_exit(_pos(bid_price=0.10), score, cfg)
    assert sig is not None
    assert sig.reason == ExitReason.MLB_M1_SEVENTH_DEFICIT_5


def test_hold_mid_game(cfg):
    """Mid-game tied state → None (HOLD)."""
    score = {
        "period_number": 4,
        "outs": 0,
        "home_score": 2,
        "away_score": 2,
        "is_home_position": True,
    }
    sig = check_mlb_score_exit(_pos(bid_price=0.50), score, cfg)
    assert sig is None


def test_inning_key_fallback(cfg):
    """Uses 'inning' key when 'period_number' absent."""
    score = {"inning": 7, "outs": 0, "home_score": 0, "away_score": 6, "is_home_position": True}
    sig = check_mlb_score_exit(_pos(bid_price=0.10), score, cfg)
    assert sig is not None
    assert sig.reason == ExitReason.MLB_M1_SEVENTH_DEFICIT_5
