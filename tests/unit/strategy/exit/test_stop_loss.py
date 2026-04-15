"""stop_loss.py için birim testler (TDD §6.7)."""
from __future__ import annotations

from src.models.position import Position
from src.strategy.exit.stop_loss import check, compute_stop_loss_pct


def _pos(**over) -> Position:
    base = dict(
        condition_id="c1", token_id="t", direction="BUY_YES",
        entry_price=0.40, size_usdc=40, shares=100,
        current_price=0.40, anchor_probability=0.55,
        confidence="B", sport_tag="nba",
    )
    base.update(over)
    return Position(**base)


def test_stale_price_skip_returns_none() -> None:
    p = _pos(current_price=0.0005, entry_price=0.40)
    assert compute_stop_loss_pct(p) is None


def test_totals_market_skip() -> None:
    p = _pos(question="Total over/under 215.5?", slug="nba-totals")
    assert compute_stop_loss_pct(p) is None


def test_spread_keyword_skip() -> None:
    p = _pos(slug="nba-lakers-spread-2026")
    assert compute_stop_loss_pct(p) is None


def test_ultra_low_entry_wide_50pct() -> None:
    p = _pos(entry_price=0.08)  # < 9c
    assert compute_stop_loss_pct(p) == 0.50


def test_low_entry_9c_top_60pct() -> None:
    p = _pos(entry_price=0.09)  # exactly at 9c
    # 60% - 0*(60-40) = 60%
    assert abs(compute_stop_loss_pct(p) - 0.60) < 1e-9


def test_low_entry_20c_bottom_40pct() -> None:
    p = _pos(entry_price=0.199)  # just under 20c (upper bound non-inclusive)
    # t≈1, 60 - 1*(60-40) = 40
    assert compute_stop_loss_pct(p) < 0.41


def test_low_entry_mid_linear() -> None:
    p = _pos(entry_price=0.145)  # midpoint
    # t=0.5, 60 - 0.5*20 = 50
    assert abs(compute_stop_loss_pct(p) - 0.50) < 1e-3


def test_sport_specific_nba() -> None:
    p = _pos(entry_price=0.40, sport_tag="nba")
    # NBA stop_loss_pct = 0.35 (sport_rules.py)
    assert compute_stop_loss_pct(p) == 0.35


def test_sport_specific_mlb() -> None:
    p = _pos(entry_price=0.40, sport_tag="mlb")
    assert compute_stop_loss_pct(p) == 0.30


def test_reentry_tightens_flat() -> None:
    p = _pos(entry_price=0.40, sport_tag="nba", sl_reentry_count=1)
    # 0.35 × 0.75 = 0.2625
    assert abs(compute_stop_loss_pct(p) - 0.2625) < 1e-6


def test_buy_no_uses_token_native_entry() -> None:
    # BUY_NO entry_price = NO token fiyatı (owned side, zaten effective).
    # entry=0.15 (NO token 15¢) → low-entry graduated path.
    # t = (0.15 - 0.09) / (0.20 - 0.09) ≈ 0.545
    # sl = 0.60 - 0.545 × 0.20 ≈ 0.491
    p = _pos(entry_price=0.15, direction="BUY_NO", current_price=0.15)
    sl = compute_stop_loss_pct(p)
    assert 0.40 < sl < 0.60  # low-entry graduated path aralığında


def test_buy_no_favorite_sport_specific() -> None:
    # BUY_NO entry_price = NO token fiyatı. 0.75 (NO token 75¢) → sport-specific path.
    p = _pos(entry_price=0.75, direction="BUY_NO", current_price=0.75, sport_tag="nba")
    assert compute_stop_loss_pct(p) == 0.35


def test_check_triggers_when_pnl_below_sl() -> None:
    # entry 0.40 → nba sl 35%; current 0.20 → pnl_pct = (20-40)/40 = -50%
    p = _pos(entry_price=0.40, current_price=0.20, size_usdc=40, shares=100)
    assert check(p) is True


def test_check_no_trigger_when_pnl_above_sl() -> None:
    # entry 0.40 → nba sl 35%; current 0.30 → pnl_pct = -25%
    p = _pos(entry_price=0.40, current_price=0.30, size_usdc=40, shares=100)
    assert check(p) is False
