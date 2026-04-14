"""graduated_sl.py için birim testler (TDD §6.8)."""
from __future__ import annotations

from src.models.position import Position
from src.strategy.exit.graduated_sl import (
    check,
    compute_momentum_multiplier,
    get_entry_price_multiplier,
    get_graduated_max_loss,
)


def _pos(**over) -> Position:
    base = dict(
        condition_id="c", token_id="t", direction="BUY_YES",
        entry_price=0.40, size_usdc=40, shares=100,
        current_price=0.40, anchor_probability=0.55,
    )
    base.update(over)
    return Position(**base)


# ── entry price multiplier ──

def test_price_mult_underdog() -> None:
    assert get_entry_price_multiplier(0.15) == 1.50


def test_price_mult_mid_underdog() -> None:
    assert get_entry_price_multiplier(0.30) == 1.25


def test_price_mult_coin_flip() -> None:
    assert get_entry_price_multiplier(0.50) == 1.00


def test_price_mult_favorite() -> None:
    assert get_entry_price_multiplier(0.65) == 0.85


def test_price_mult_heavy_fav() -> None:
    assert get_entry_price_multiplier(0.75) == 0.70


# ── base tier ──

def test_base_tier_early() -> None:
    # elapsed 0.10, entry 0.40 (mult 1.0), score neutral → 0.40 × 1.0 × 1.0 = 0.40
    assert get_graduated_max_loss(0.10, 0.40, {}) == 0.40


def test_base_tier_mid() -> None:
    # elapsed 0.50 → 0.30 × 1.0 × 1.0 = 0.30
    assert get_graduated_max_loss(0.50, 0.40, {}) == 0.30


def test_base_tier_late() -> None:
    assert get_graduated_max_loss(0.70, 0.40, {}) == 0.20


def test_base_tier_final() -> None:
    assert get_graduated_max_loss(0.90, 0.40, {}) == 0.15


def test_pre_match_uses_early_base() -> None:
    assert get_graduated_max_loss(-0.1, 0.40, {}) == 0.40


# ── score adjustment ──

def test_score_ahead_loosens() -> None:
    # 0.40 × 1.0 × 1.25 = 0.50
    assert abs(get_graduated_max_loss(0.10, 0.40, {"available": True, "map_diff": 1}) - 0.50) < 1e-9


def test_score_behind_tightens() -> None:
    # 0.40 × 1.0 × 0.75 = 0.30
    assert abs(get_graduated_max_loss(0.10, 0.40, {"available": True, "map_diff": -1}) - 0.30) < 1e-9


def test_clamp_min() -> None:
    # Final phase + behind + favorite: 0.15 × 0.70 × 0.75 = 0.0787 → no clamp
    # Ama daha ekstrem: momentum ×0.60 eklendikten sonra 0.0472 → clamp 0.05
    result = get_graduated_max_loss(0.90, 0.75, {"available": True, "map_diff": -1})
    assert result >= 0.05


def test_clamp_max() -> None:
    # Early + ahead + underdog: 0.40 × 1.50 × 1.25 = 0.75 → clamp 0.70
    result = get_graduated_max_loss(0.10, 0.15, {"available": True, "map_diff": 1})
    assert result == 0.70


# ── momentum tighten ──

def test_momentum_deep_tighten() -> None:
    r = compute_momentum_multiplier(consecutive_down=5, cumulative_drop=0.15)
    assert r.tighten is True
    assert r.multiplier == 0.60


def test_momentum_mild_tighten() -> None:
    r = compute_momentum_multiplier(consecutive_down=3, cumulative_drop=0.06)
    assert r.tighten is True
    assert r.multiplier == 0.75


def test_momentum_no_tighten_below_threshold() -> None:
    r = compute_momentum_multiplier(consecutive_down=2, cumulative_drop=0.10)
    assert r.tighten is False
    assert r.multiplier == 1.0


# ── check() ──

def test_check_no_exit_when_within_loss() -> None:
    # elapsed 0.10, eff_entry 0.40, base=0.40, pnl=-20% > -40% → no exit
    p = _pos(entry_price=0.40, current_price=0.32, size_usdc=40, shares=100)
    exit_now, max_loss = check(p, elapsed_pct=0.10, effective_entry=0.40)
    assert exit_now is False
    assert max_loss == 0.40


def test_check_exits_when_loss_too_big() -> None:
    # elapsed 0.70, base 0.20, pnl=-25% < -20% → exit
    p = _pos(entry_price=0.40, current_price=0.30, size_usdc=40, shares=100)
    exit_now, _ = check(p, elapsed_pct=0.70, effective_entry=0.40)
    assert exit_now is True


def test_momentum_tighten_triggers_exit_earlier() -> None:
    # elapsed 0.50 base 0.30; pnl -25%, normalde dayanır. Momentum deep → 0.30×0.60=0.18; -25%<-18% → exit
    p = _pos(
        entry_price=0.40, current_price=0.30, size_usdc=40, shares=100,
        consecutive_down_cycles=5, cumulative_drop=0.15,
    )
    exit_now, max_loss = check(p, elapsed_pct=0.50, effective_entry=0.40)
    assert exit_now is True
    assert max_loss < 0.30  # tightened
