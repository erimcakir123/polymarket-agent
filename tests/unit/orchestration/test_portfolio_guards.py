# tests/unit/orchestration/test_portfolio_guards.py
from dataclasses import dataclass
from unittest.mock import MagicMock

from src.orchestration.portfolio_guards import (
    GuardSkip,
    check_global_halts,
    check_per_market_guards,
)


@dataclass
class _MockMarket:
    condition_id: str = "cid-1"
    event_id: str = "evt-1"
    sports_market_type: str = ""  # boş → same-type guard atlanır (eski testler etkilenmez)


def _mk_breaker(halt: bool = False, reason: str = "") -> MagicMock:
    b = MagicMock()
    b.should_halt_entries.return_value = (halt, reason)
    return b


def _mk_cooldown(active: bool = False, remaining: int = 0) -> MagicMock:
    c = MagicMock()
    c.is_active.return_value = active
    c.state.cooldown_remaining = remaining
    return c


def _mk_portfolio(count: int = 0, event_counts: dict | None = None) -> MagicMock:
    p = MagicMock()
    p.count.return_value = count
    p.count_event.side_effect = lambda eid: (event_counts or {}).get(eid, 0)
    p.positions_for_event.return_value = []  # SPEC-S Faz D: default no existing positions
    return p


def _mk_blacklist(cid_set: set | None = None, eid_set: set | None = None) -> MagicMock:
    b = MagicMock()
    cids = cid_set or set()
    eids = eid_set or set()
    b.is_blacklisted.side_effect = lambda condition_id=None, event_id=None: (
        (condition_id is not None and condition_id in cids)
        or (event_id is not None and event_id in eids)
    )
    return b


def test_check_global_halts_breaker_active() -> None:
    skip = check_global_halts(
        breaker=_mk_breaker(halt=True, reason="breaker: daily_loss=-50"),
        cooldown=_mk_cooldown(),
        portfolio=_mk_portfolio(count=0),
        max_positions=50,
    )
    assert skip is not None
    assert skip.reason == "circuit_breaker"
    assert "daily_loss" in skip.detail


def test_check_global_halts_cooldown_active() -> None:
    skip = check_global_halts(
        breaker=_mk_breaker(),
        cooldown=_mk_cooldown(active=True, remaining=3),
        portfolio=_mk_portfolio(count=0),
        max_positions=50,
    )
    assert skip is not None
    assert skip.reason == "cooldown_active"
    assert "cycles_remaining=3" in skip.detail


def test_check_global_halts_max_positions() -> None:
    skip = check_global_halts(
        breaker=_mk_breaker(),
        cooldown=_mk_cooldown(),
        portfolio=_mk_portfolio(count=50),
        max_positions=50,
    )
    assert skip is not None
    assert skip.reason == "max_positions_reached"


def test_check_global_halts_passes() -> None:
    skip = check_global_halts(
        breaker=_mk_breaker(),
        cooldown=_mk_cooldown(),
        portfolio=_mk_portfolio(count=10),
        max_positions=50,
    )
    assert skip is None


def test_check_per_market_event_cap() -> None:
    market = _MockMarket(condition_id="cid-x", event_id="evt-x")
    skip = check_per_market_guards(
        market=market,
        portfolio=_mk_portfolio(event_counts={"evt-x": 3}),
        blacklist=_mk_blacklist(),
        max_positions_per_event=3,
    )
    assert skip is not None
    assert skip.reason == "event_already_held"


def test_check_per_market_blacklist_cid() -> None:
    market = _MockMarket(condition_id="cid-blocked", event_id="evt-x")
    skip = check_per_market_guards(
        market=market,
        portfolio=_mk_portfolio(),
        blacklist=_mk_blacklist(cid_set={"cid-blocked"}),
        max_positions_per_event=3,
    )
    assert skip is not None
    assert skip.reason == "blacklisted"
    assert "condition_id" in skip.detail


def test_check_per_market_blacklist_eid() -> None:
    market = _MockMarket(condition_id="cid-x", event_id="evt-blocked")
    skip = check_per_market_guards(
        market=market,
        portfolio=_mk_portfolio(),
        blacklist=_mk_blacklist(eid_set={"evt-blocked"}),
        max_positions_per_event=3,
    )
    assert skip is not None
    assert skip.reason == "blacklisted"
    assert "event_id" in skip.detail


def test_check_per_market_passes() -> None:
    market = _MockMarket(condition_id="cid-ok", event_id="evt-ok")
    skip = check_per_market_guards(
        market=market,
        portfolio=_mk_portfolio(event_counts={"evt-ok": 0}),
        blacklist=_mk_blacklist(),
        max_positions_per_event=3,
    )
    assert skip is None
