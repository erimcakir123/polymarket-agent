"""Score exit (K1-K4) testleri (SPEC-004 Adım 3)."""
from __future__ import annotations

from src.models.enums import ExitReason
from src.strategy.exit.hockey_score_exit import check


def _info(deficit: int = 0, available: bool = True) -> dict:
    return {"available": available, "deficit": deficit, "map_diff": -deficit}


# ── K1: deficit >= 3 hemen çık ──

def test_score_exit_deficit_3_immediate_exit() -> None:
    sig = check("nhl", "A", _info(deficit=3), elapsed_pct=0.30, current_price=0.40)
    assert sig is not None
    assert sig.reason == ExitReason.SCORE_EXIT
    assert "K1" in sig.detail


def test_score_exit_deficit_5_immediate_exit() -> None:
    sig = check("nhl", "A", _info(deficit=5), elapsed_pct=0.10, current_price=0.60)
    assert sig is not None
    assert "K1" in sig.detail


# ── K2: deficit >= 2 + elapsed >= 0.67 ──

def test_score_exit_deficit_2_late_game_exit() -> None:
    sig = check("nhl", "A", _info(deficit=2), elapsed_pct=0.70, current_price=0.40)
    assert sig is not None
    assert "K2" in sig.detail


def test_score_exit_deficit_2_early_game_hold() -> None:
    sig = check("nhl", "A", _info(deficit=2), elapsed_pct=0.30, current_price=0.40)
    assert sig is None


# ── K3: deficit >= 2 + price < 0.35 ──

def test_score_exit_deficit_2_low_price_exit() -> None:
    sig = check("nhl", "A", _info(deficit=2), elapsed_pct=0.30, current_price=0.30)
    assert sig is not None
    assert "K3" in sig.detail


# ── K4: deficit >= 1 + elapsed >= 0.92 ──

def test_score_exit_deficit_1_last_5min_exit() -> None:
    sig = check("nhl", "A", _info(deficit=1), elapsed_pct=0.93, current_price=0.45)
    assert sig is not None
    assert "K4" in sig.detail


def test_score_exit_deficit_1_midgame_hold() -> None:
    sig = check("nhl", "A", _info(deficit=1), elapsed_pct=0.50, current_price=0.45)
    assert sig is None


# ── Guard: score yok / önde / hockey değil / B-conf ──

def test_score_exit_no_score_no_exit() -> None:
    sig = check("nhl", "A", _info(available=False), elapsed_pct=0.90, current_price=0.20)
    assert sig is None


def test_score_exit_ahead_no_exit() -> None:
    sig = check("nhl", "A", _info(deficit=-2), elapsed_pct=0.95, current_price=0.90)
    assert sig is None


def test_score_exit_not_hockey_no_exit() -> None:
    sig = check("mlb", "A", _info(deficit=5), elapsed_pct=0.90, current_price=0.10)
    assert sig is None


def test_score_exit_b_conf_no_exit() -> None:
    sig = check("nhl", "B", _info(deficit=4), elapsed_pct=0.90, current_price=0.10)
    assert sig is None
