"""Unit tests for _mlb_run_line_dispatch.py — MLB run line exit dispatcher."""
from types import SimpleNamespace

import pytest

from src.models.enums import ExitReason
from src.strategy.exit._mlb_run_line_dispatch import check_mlb_run_line_exit
from src.strategy.exit.mlb_run_line_exit import MLBRunLineExitConfig


@pytest.fixture
def cfg():
    return MLBRunLineExitConfig(
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
    assert check_mlb_run_line_exit(_pos(), score, cfg) is None


def test_missing_score_returns_none(cfg):
    """Missing score values → None."""
    score = {"period_number": 5, "home_score": None, "away_score": None}
    assert check_mlb_run_line_exit(_pos(), score, cfg) is None


def test_near_resolve_routes(cfg):
    """High bid → near-resolve signal."""
    score = {"period_number": 5, "outs": 0, "home_score": 4, "away_score": 1}
    sig = check_mlb_run_line_exit(_pos(bid_price=0.96), score, cfg)
    assert sig is not None
    assert sig.reason == ExitReason.MLB_RUN_LINE_NEAR_RESOLVE
    assert sig.partial is False


def test_m1_seventh_deficit_five(cfg):
    """Inning 7, deficit 5 (RL coverage dead same as ML) → M1_SEVENTH_DEFICIT_5."""
    score = {
        "period_number": 7,
        "outs": 0,
        "home_score": 0,
        "away_score": 5,
        "is_home_position": True,
    }
    sig = check_mlb_run_line_exit(_pos(bid_price=0.08), score, cfg)
    assert sig is not None
    assert sig.reason == ExitReason.MLB_M1_SEVENTH_DEFICIT_5


def test_m2_eighth_deficit_three(cfg):
    """Inning 8, deficit 3 → M2_EIGHTH_DEFICIT_3."""
    score = {
        "period_number": 8,
        "outs": 0,
        "home_score": 0,
        "away_score": 3,
        "is_home_position": True,
    }
    sig = check_mlb_run_line_exit(_pos(bid_price=0.10), score, cfg)
    assert sig is not None
    assert sig.reason == ExitReason.MLB_M2_EIGHTH_DEFICIT_3


def test_m3_ninth_deficit_one(cfg):
    """Inning 9, backed away, home leads 1 → M3_NINTH_DEFICIT_1."""
    score = {
        "period_number": 9,
        "outs": 1,
        "home_score": 3,
        "away_score": 2,
        "is_home_position": False,
    }
    sig = check_mlb_run_line_exit(_pos(bid_price=0.10), score, cfg)
    assert sig is not None
    assert sig.reason == ExitReason.MLB_M3_NINTH_DEFICIT_1


def test_hold_early_game(cfg):
    """Early game tied → None (HOLD)."""
    score = {
        "period_number": 3,
        "outs": 0,
        "home_score": 1,
        "away_score": 1,
        "is_home_position": True,
    }
    sig = check_mlb_run_line_exit(_pos(bid_price=0.50), score, cfg)
    assert sig is None
