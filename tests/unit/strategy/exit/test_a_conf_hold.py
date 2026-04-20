"""a_conf_hold.py için birim testler (market_flip_exit)."""
from __future__ import annotations

from src.models.position import Position
from src.strategy.exit.a_conf_hold import market_flip_exit


def _pos(**over) -> Position:
    base = dict(
        condition_id="c", token_id="t", direction="BUY_YES",
        entry_price=0.65, size_usdc=40, shares=60, current_price=0.65,
        anchor_probability=0.70, confidence="A",
    )
    base.update(over)
    return Position(**base)


# ── market_flip_exit ──

def test_early_match_flip_ignored() -> None:
    # elapsed < 0.85 → flip asla tetiklenmez
    p = _pos(entry_price=0.65, current_price=0.30)
    assert market_flip_exit(p, elapsed_pct=0.50) is False
    assert market_flip_exit(p, elapsed_pct=0.84) is False


def test_late_match_flip_triggers_below_50c() -> None:
    p = _pos(entry_price=0.65, current_price=0.40)  # eff = 0.40 < 0.50
    assert market_flip_exit(p, elapsed_pct=0.85) is True


def test_late_match_no_flip_above_50c() -> None:
    p = _pos(entry_price=0.65, current_price=0.55)  # eff 0.55 >= 0.50
    assert market_flip_exit(p, elapsed_pct=0.90) is False


def test_flip_buy_no_uses_token_native() -> None:
    # BUY_NO current_price = NO token fiyatı. 0.40 < 0.50 → owned flip'e düştü.
    p = _pos(entry_price=0.65, direction="BUY_NO", current_price=0.40)
    assert market_flip_exit(p, elapsed_pct=0.90) is True
