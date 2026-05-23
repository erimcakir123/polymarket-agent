"""PortfolioManager.positions_for_event() için birim testler (SPEC-S Faz D)."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.domain.portfolio.manager import PortfolioManager


def _mock_position(cid: str, event_id: str, market_type: str = "moneyline") -> MagicMock:
    p = MagicMock()
    p.condition_id = cid
    p.event_id = event_id
    p.sports_market_type = market_type
    return p


def test_positions_for_event_returns_matching() -> None:
    pm = PortfolioManager(initial_bankroll=1000)
    pm.positions = {
        "c1": _mock_position("c1", "e1"),
        "c2": _mock_position("c2", "e1"),
        "c3": _mock_position("c3", "e2"),
    }
    result = pm.positions_for_event("e1")
    assert len(result) == 2
    assert {p.condition_id for p in result} == {"c1", "c2"}


def test_positions_for_event_other_event() -> None:
    pm = PortfolioManager(initial_bankroll=1000)
    pm.positions = {
        "c1": _mock_position("c1", "e1"),
        "c2": _mock_position("c2", "e2"),
    }
    result = pm.positions_for_event("e2")
    assert len(result) == 1
    assert result[0].condition_id == "c2"


def test_positions_for_event_empty_string_returns_empty() -> None:
    pm = PortfolioManager(initial_bankroll=1000)
    pm.positions = {"c1": _mock_position("c1", "e1")}
    assert pm.positions_for_event("") == []


def test_positions_for_event_no_match_returns_empty() -> None:
    pm = PortfolioManager(initial_bankroll=1000)
    pm.positions = {"c1": _mock_position("c1", "e1")}
    assert pm.positions_for_event("e99") == []
