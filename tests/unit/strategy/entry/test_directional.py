"""Directional entry (SPEC-017) unit tests."""
from __future__ import annotations

import pytest

from src.models.enums import Direction
from src.models.market import MarketData
from src.strategy.entry.directional import evaluate_directional


def _make_market(yes_price: float = 0.70, liquidity: float = 10_000.0) -> MarketData:
    """Test fixture — minimal MarketData."""
    return MarketData(
        condition_id="0xabc",
        yes_token_id="tkYES",
        no_token_id="tkNO",
        slug="test-match-2026-04-20",
        question="Team A vs Team B",
        yes_price=yes_price,
        no_price=1.0 - yes_price,
        liquidity=liquidity,
        volume_24h=1000.0,
        sport_tag="test",
        event_id="evt1",
        end_date_iso="2026-04-27T00:00:00Z",
        match_start_iso="2026-04-20T12:00:00Z",
    )


def test_directional_buy_yes_when_anchor_above_50():
    market = _make_market(yes_price=0.70)
    signal = evaluate_directional(
        market=market, anchor=0.75, confidence="A",
        min_favorite_probability=0.55, min_entry_price=0.60, max_entry_price=0.85,
    )
    assert signal is not None
    assert signal.direction == Direction.BUY_YES
    assert signal.anchor_probability == 0.75


def test_directional_buy_no_when_anchor_below_50():
    # yes_price=0.30 → BUY_NO effective entry = 1-0.30 = 0.70 (in range)
    market = _make_market(yes_price=0.30)
    signal = evaluate_directional(
        market=market, anchor=0.25, confidence="A",
        min_favorite_probability=0.55, min_entry_price=0.60, max_entry_price=0.85,
    )
    assert signal is not None
    assert signal.direction == Direction.BUY_NO
    assert signal.anchor_probability == 0.25


def test_directional_skips_when_win_prob_below_threshold():
    market = _make_market(yes_price=0.65)
    signal = evaluate_directional(
        market=market, anchor=0.52, confidence="A",
        min_favorite_probability=0.55, min_entry_price=0.60, max_entry_price=0.85,
    )
    assert signal is None


def test_directional_skips_when_effective_price_below_min():
    market = _make_market(yes_price=0.58)
    signal = evaluate_directional(
        market=market, anchor=0.65, confidence="A",
        min_favorite_probability=0.55, min_entry_price=0.60, max_entry_price=0.85,
    )
    assert signal is None


def test_directional_skips_when_effective_price_above_max():
    market = _make_market(yes_price=0.90)
    signal = evaluate_directional(
        market=market, anchor=0.92, confidence="A",
        min_favorite_probability=0.55, min_entry_price=0.60, max_entry_price=0.85,
    )
    assert signal is None


def test_directional_buy_no_effective_price_computed_correctly():
    # yes_price=0.20 → effective entry = 0.80, within range [0.60, 0.85]
    market = _make_market(yes_price=0.20)
    signal = evaluate_directional(
        market=market, anchor=0.18, confidence="A",
        min_favorite_probability=0.55, min_entry_price=0.60, max_entry_price=0.85,
    )
    assert signal is not None
    assert signal.direction == Direction.BUY_NO


def test_directional_anchor_exactly_fifty_with_relaxed_threshold_chooses_yes():
    """anchor=0.50 is tie-breaker → BUY_YES (>= comparison).

    Uses relaxed min_favorite_probability=0.50 to isolate direction logic
    from production fav-prob filter (which would reject this at 0.55).
    """
    market = _make_market(yes_price=0.65)
    signal = evaluate_directional(
        market=market, anchor=0.50, confidence="A",
        min_favorite_probability=0.50, min_entry_price=0.60, max_entry_price=0.85,
    )
    assert signal is not None
    assert signal.direction == Direction.BUY_YES


def test_directional_anchor_exactly_fifty_rejected_by_production_threshold():
    """Production default (0.55): anchor=0.50 fails favorite filter → None."""
    market = _make_market(yes_price=0.65)
    signal = evaluate_directional(
        market=market, anchor=0.50, confidence="A",
        min_favorite_probability=0.55, min_entry_price=0.60, max_entry_price=0.85,
    )
    assert signal is None


def test_directional_anchor_just_below_fifty_chooses_no():
    """anchor=0.49 → BUY_NO branch (< comparison, not <=)."""
    market = _make_market(yes_price=0.30)  # BUY_NO effective = 0.70, in range
    signal = evaluate_directional(
        market=market, anchor=0.49, confidence="A",
        min_favorite_probability=0.50, min_entry_price=0.60, max_entry_price=0.85,
    )
    assert signal is not None
    assert signal.direction == Direction.BUY_NO
