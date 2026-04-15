"""Position için birim testler."""
from __future__ import annotations

from datetime import datetime

import pytest

from src.models.position import Position, effective_price


def _valid(**overrides) -> Position:
    base = dict(
        condition_id="0x1",
        token_id="tok",
        direction="BUY_YES",
        entry_price=0.40,
        size_usdc=40.0,
        shares=100.0,
        current_price=0.40,
        anchor_probability=0.55,
    )
    base.update(overrides)
    return Position(**base)


def test_position_anchor_probability_valid() -> None:
    p = _valid(anchor_probability=0.55)
    assert p.anchor_probability == 0.55


def test_position_anchor_probability_too_low_raises() -> None:
    with pytest.raises(Exception):
        _valid(anchor_probability=0.005)


def test_position_anchor_probability_too_high_raises() -> None:
    with pytest.raises(Exception):
        _valid(anchor_probability=0.995)


def test_effective_price_buy_yes() -> None:
    assert effective_price(0.40, "BUY_YES") == 0.40


def test_effective_price_buy_no() -> None:
    assert abs(effective_price(0.40, "BUY_NO") - 0.60) < 1e-9


def test_position_unrealized_pnl_pct_buy_yes_profit() -> None:
    p = _valid(entry_price=0.40, current_price=0.50, shares=100.0, size_usdc=40.0)
    # current_value = 100 * 0.50 = 50; pnl = 10; pct = 0.25
    assert abs(p.unrealized_pnl_pct - 0.25) < 1e-9


def test_position_unrealized_pnl_pct_buy_no_loss_when_no_price_drops() -> None:
    # BUY_NO: pozisyon NO token'dan oluşur. NO fiyatı düşerse LOSS.
    # entry NO=0.40, current NO=0.30, shares=100, size=$40
    # current_value = shares × current_price = 100 × 0.30 = 30
    # pnl = 30 - 40 = -10 = -25%
    p = _valid(direction="BUY_NO", entry_price=0.40, current_price=0.30, shares=100.0, size_usdc=40.0)
    assert abs(p.unrealized_pnl_pct - (-0.25)) < 1e-9


def test_position_unrealized_pnl_pct_buy_no_profit_when_no_price_rises() -> None:
    # BUY_NO: NO token fiyatı yükselirse PROFIT.
    # entry NO=0.40, current NO=0.60, shares=100, size=$40
    # current_value = 100 × 0.60 = 60, pnl = 20 = +50%
    p = _valid(direction="BUY_NO", entry_price=0.40, current_price=0.60, shares=100.0, size_usdc=40.0)
    assert abs(p.unrealized_pnl_pct - 0.50) < 1e-9


def test_position_unrealized_pnl_zero_at_entry_buy_no() -> None:
    # Entry anında (current_price == entry_price) PnL sıfır olmalı — direction'dan bağımsız.
    # BUY_NO regression: eski formülde aynı fiyatta current_value ≠ size_usdc idi.
    p = _valid(direction="BUY_NO", entry_price=0.30, current_price=0.30, shares=166.67, size_usdc=50.0)
    assert abs(p.unrealized_pnl_usdc) < 0.01  # ≈0 (float tolerans)


def test_position_unrealized_pnl_zero_at_entry_buy_yes() -> None:
    # Entry anında BUY_YES için de PnL sıfır (regresyon koruma).
    p = _valid(direction="BUY_YES", entry_price=0.70, current_price=0.70, shares=71.43, size_usdc=50.0)
    assert abs(p.unrealized_pnl_usdc) < 0.01


def test_position_defaults() -> None:
    p = _valid()
    assert p.confidence == "B"
    assert p.scale_out_tier == 0
    assert p.partial_exits == []
    assert p.sl_reentry_count == 0
    assert p.ever_in_profit is False
    assert p.favored is False
    assert isinstance(p.entry_timestamp, datetime)


def test_position_json_roundtrip() -> None:
    p = _valid(confidence="A", event_id="evt_99")
    data = p.model_dump(mode="json")
    restored = Position(**data)
    assert restored.confidence == "A"
    assert restored.event_id == "evt_99"
    assert restored.anchor_probability == 0.55
