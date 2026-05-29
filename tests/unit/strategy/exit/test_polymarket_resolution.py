"""polymarket_resolution.check_resolution birim testleri (2026-05-28).

Polymarket resolved market icin owned-side payout hesabini dogrular.
Pure decision — I/O yok, gamma response dict dogrudan parametre.
"""
from __future__ import annotations

from src.models.position import Position
from src.strategy.exit.polymarket_resolution import (
    ResolvedSignal,
    check_resolution,
)


def _pos(direction: str = "BUY_YES") -> Position:
    return Position(
        condition_id="cid",
        token_id="tok",
        direction=direction,
        entry_price=0.5,
        size_usdc=50.0,
        shares=100.0,
        current_price=0.5,
        anchor_probability=0.5,
        slug="test-market",
    )


def test_check_resolution_returns_none_when_market_is_none() -> None:
    assert check_resolution(_pos(), None) is None


def test_check_resolution_returns_none_when_market_not_closed() -> None:
    market = {"closed": False, "umaResolutionStatus": "resolved",
              "outcomePrices": '["1", "0"]'}
    assert check_resolution(_pos(), market) is None


def test_check_resolution_returns_none_when_uma_not_resolved() -> None:
    market = {"closed": True, "umaResolutionStatus": "proposed",
              "outcomePrices": '["1", "0"]'}
    assert check_resolution(_pos(), market) is None


def test_check_resolution_returns_signal_buy_yes_won() -> None:
    """prices=['1','0'] + BUY_YES → payout 1.0."""
    market = {"closed": True, "umaResolutionStatus": "resolved",
              "outcomePrices": '["1", "0"]'}
    signal = check_resolution(_pos("BUY_YES"), market)
    assert isinstance(signal, ResolvedSignal)
    assert signal.exit_price == 1.0


def test_check_resolution_returns_signal_buy_yes_lost() -> None:
    """prices=['0','1'] + BUY_YES → payout 0.0."""
    market = {"closed": True, "umaResolutionStatus": "resolved",
              "outcomePrices": '["0", "1"]'}
    signal = check_resolution(_pos("BUY_YES"), market)
    assert isinstance(signal, ResolvedSignal)
    assert signal.exit_price == 0.0


def test_check_resolution_returns_signal_buy_no_won() -> None:
    """prices=['0','1'] + BUY_NO → NO token won → payout 1.0."""
    market = {"closed": True, "umaResolutionStatus": "resolved",
              "outcomePrices": '["0", "1"]'}
    signal = check_resolution(_pos("BUY_NO"), market)
    assert isinstance(signal, ResolvedSignal)
    assert signal.exit_price == 1.0


def test_check_resolution_returns_signal_buy_no_lost() -> None:
    """prices=['1','0'] + BUY_NO → NO token lost → payout 0.0."""
    market = {"closed": True, "umaResolutionStatus": "resolved",
              "outcomePrices": '["1", "0"]'}
    signal = check_resolution(_pos("BUY_NO"), market)
    assert isinstance(signal, ResolvedSignal)
    assert signal.exit_price == 0.0


def test_check_resolution_handles_malformed_prices_returns_none() -> None:
    """Bozuk JSON / eksik liste → None (sessiz crash yok)."""
    market = {"closed": True, "umaResolutionStatus": "resolved",
              "outcomePrices": "not-json"}
    assert check_resolution(_pos(), market) is None

    market2 = {"closed": True, "umaResolutionStatus": "resolved",
               "outcomePrices": '["1"]'}  # eksik
    assert check_resolution(_pos(), market2) is None


def test_check_resolution_handles_already_parsed_list() -> None:
    """outcomePrices zaten list ise (gamma bazi response variantlari) parse calismali."""
    market = {"closed": True, "umaResolutionStatus": "resolved",
              "outcomePrices": ["1", "0"]}
    signal = check_resolution(_pos("BUY_YES"), market)
    assert isinstance(signal, ResolvedSignal)
    assert signal.exit_price == 1.0
