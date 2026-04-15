"""favored.py için birim testler (TDD §6.13)."""
from __future__ import annotations

from src.models.position import Position
from src.strategy.exit.favored import should_demote, should_promote


def _pos(**over) -> Position:
    base = dict(
        condition_id="c", token_id="t", direction="BUY_YES",
        entry_price=0.50, size_usdc=40, shares=80,
        current_price=0.50, anchor_probability=0.55, confidence="B",
    )
    base.update(over)
    return Position(**base)


# ── should_promote ──

def test_promote_when_eff_high_and_ab_conf() -> None:
    p = _pos(current_price=0.70, confidence="B")
    assert should_promote(p) is True


def test_promote_at_threshold() -> None:
    p = _pos(current_price=0.65, confidence="A")
    assert should_promote(p) is True


def test_no_promote_below_threshold() -> None:
    p = _pos(current_price=0.60, confidence="A")
    assert should_promote(p) is False


def test_no_promote_for_c_conf() -> None:
    p = _pos(current_price=0.70, confidence="C")
    assert should_promote(p) is False


def test_no_promote_already_favored() -> None:
    p = _pos(current_price=0.70, favored=True)
    assert should_promote(p) is False


def test_promote_buy_no_uses_effective() -> None:
    # BUY_NO current 0.30 → eff 0.70 → promote
    p = _pos(current_price=0.30, direction="BUY_NO", confidence="B")
    assert should_promote(p) is True


# ── should_demote ──

def test_demote_favored_when_drops_below_threshold() -> None:
    p = _pos(current_price=0.60, favored=True)
    assert should_demote(p) is True


def test_no_demote_when_above_threshold() -> None:
    p = _pos(current_price=0.70, favored=True)
    assert should_demote(p) is False


def test_no_demote_not_favored() -> None:
    p = _pos(current_price=0.50, favored=False)
    assert should_demote(p) is False
