"""check_per_market_guards same_market_type_per_event guard için birim testler (SPEC-S Faz D)."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.orchestration.portfolio_guards import check_per_market_guards


def _market(cid: str, event_id: str | None, sports_market_type: object) -> MagicMock:
    m = MagicMock()
    m.condition_id = cid
    m.event_id = event_id
    m.sports_market_type = sports_market_type
    return m


def _position(sports_market_type: object) -> MagicMock:
    p = MagicMock()
    p.sports_market_type = sports_market_type
    return p


def _portfolio(count: int, positions: list) -> MagicMock:
    pf = MagicMock()
    pf.count_event.return_value = count
    pf.positions_for_event.return_value = positions
    return pf


def _blacklist_clean() -> MagicMock:
    bl = MagicMock()
    bl.is_blacklisted.return_value = False
    return bl


def test_second_totals_in_same_event_blocked() -> None:
    pf = _portfolio(count=1, positions=[_position("totals")])
    market = _market("c2", "e1", "totals")
    result = check_per_market_guards(
        market=market, portfolio=pf, blacklist=_blacklist_clean(),
        max_positions_per_event=3,
    )
    assert result is not None
    assert result.reason == "same_market_type_per_event"


def test_different_types_in_same_event_allowed() -> None:
    pf = _portfolio(count=1, positions=[_position("moneyline")])
    market = _market("c2", "e1", "totals")
    result = check_per_market_guards(
        market=market, portfolio=pf, blacklist=_blacklist_clean(),
        max_positions_per_event=3,
    )
    assert result is None


def test_event_cap_at_3_still_takes_priority() -> None:
    pf = _portfolio(count=3, positions=[
        _position("moneyline"), _position("totals"), _position("spreads"),
    ])
    market = _market("c4", "e1", "moneyline")
    result = check_per_market_guards(
        market=market, portfolio=pf, blacklist=_blacklist_clean(),
        max_positions_per_event=3,
    )
    assert result is not None
    assert result.reason == "event_already_held"


def test_enum_and_string_market_types_normalize_equivalently() -> None:
    """SportsMarketType enum ile string 'totals' aynı tür olarak tanınır."""
    from src.models.enums import SportsMarketType
    pf = _portfolio(count=1, positions=[_position(SportsMarketType.TOTALS)])
    market = _market("c2", "e1", "totals")  # market'ten string gelir
    result = check_per_market_guards(
        market=market, portfolio=pf, blacklist=_blacklist_clean(),
        max_positions_per_event=3,
    )
    assert result is not None
    assert result.reason == "same_market_type_per_event"


def test_empty_market_type_does_not_block_anything() -> None:
    """sports_market_type = '' (eski/test market) → same-type kontrolü atlanır."""
    pf = _portfolio(count=1, positions=[_position("moneyline")])
    market = _market("c2", "e1", "")
    result = check_per_market_guards(
        market=market, portfolio=pf, blacklist=_blacklist_clean(),
        max_positions_per_event=3,
    )
    assert result is None
