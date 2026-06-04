"""EntryProcessor.process_signals — model-anchor entry path tests (SPEC-R)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.models.enums import Direction, EntryReason
from src.models.signal import Signal
from src.orchestration.entry_processor import EntryProcessor


def _mk_signal(cid: str = "cid-1", edge: float = 0.08) -> Signal:
    return Signal(
        condition_id=cid,
        direction=Direction.BUY_YES,
        anchor_probability=0.65,
        market_price=0.57,
        edge=edge,
        confidence="A",
        size_usdc=50.0,
        entry_reason=EntryReason.MLB_SUBMARKET,
        bookmaker_prob=0.0,
        num_bookmakers=0,
        has_sharp=False,
        sport_tag="baseball_mlb",
        event_id="evt-1",
    )


def _mk_market(cid: str = "cid-1"):
    m = MagicMock()
    m.condition_id = cid
    m.event_id = "evt-1"
    m.question = "test"
    m.liquidity = 100000.0
    m.yes_price = 0.57
    m.slug = f"slug-{cid}"
    m.token_id = f"tok-{cid}"
    m.match_start_iso = ""
    m.end_date_iso = ""
    return m


def _mk_deps(circuit_halt: bool = False, cooldown_active: bool = False,
             max_positions: int = 50, portfolio_count: int = 0,
             event_count: int = 0, blacklisted: bool = False) -> MagicMock:
    deps = MagicMock()
    deps.state.config.mode.value = "dry_run"
    deps.gate.config.max_positions = max_positions
    deps.gate.config.max_positions_per_event = 3
    deps.state.portfolio.count.return_value = portfolio_count
    deps.state.portfolio.count_event.return_value = event_count
    deps.circuit_breaker.should_halt_entries.return_value = (circuit_halt, "")
    deps.cooldown.is_active.return_value = cooldown_active
    deps.cooldown.state.cooldown_remaining = 0
    deps.blacklist.is_blacklisted.return_value = blacklisted
    deps.executor.execute.return_value = MagicMock(
        filled=True, avg_price=0.57, size_usdc=50.0,
    )
    return deps


def test_process_signals_empty_input_no_op() -> None:
    deps = _mk_deps()
    processor = EntryProcessor(deps)
    processor.process_signals(markets=[], signals=[])
    deps.executor.execute.assert_not_called()


def test_process_signals_length_mismatch_raises() -> None:
    deps = _mk_deps()
    processor = EntryProcessor(deps)
    with pytest.raises(ValueError, match="length mismatch"):
        processor.process_signals(markets=[_mk_market()], signals=[])


def test_process_signals_circuit_breaker_halts() -> None:
    deps = _mk_deps(circuit_halt=True)
    processor = EntryProcessor(deps)
    processor.process_signals(markets=[_mk_market()], signals=[_mk_signal()])
    deps.executor.execute.assert_not_called()


def test_process_signals_cooldown_halts() -> None:
    deps = _mk_deps(cooldown_active=True)
    processor = EntryProcessor(deps)
    processor.process_signals(markets=[_mk_market()], signals=[_mk_signal()])
    deps.executor.execute.assert_not_called()


def test_process_signals_max_positions_halts() -> None:
    deps = _mk_deps(max_positions=10, portfolio_count=10)
    processor = EntryProcessor(deps)
    processor.process_signals(markets=[_mk_market()], signals=[_mk_signal()])
    deps.executor.execute.assert_not_called()


def test_process_signals_event_cap_skips_individual() -> None:
    """Event_cap dolu market skip; diğer market'ler geçer."""
    deps = _mk_deps()
    deps.state.portfolio.count_event.side_effect = lambda eid: (
        3 if eid == "evt-blocked" else 0
    )
    m1 = _mk_market("cid-1")
    m1.event_id = "evt-blocked"
    m2 = _mk_market("cid-2")
    m2.event_id = "evt-ok"
    processor = EntryProcessor(deps)
    processor.process_signals(
        markets=[m1, m2],
        signals=[_mk_signal("cid-1"), _mk_signal("cid-2")],
    )
    assert deps.executor.execute.call_count == 1


def test_process_signals_blacklist_skips_individual() -> None:
    deps = _mk_deps()
    deps.blacklist.is_blacklisted.side_effect = lambda condition_id="", event_id="": (
        condition_id == "cid-blocked"
    )
    m1 = _mk_market("cid-blocked")
    m2 = _mk_market("cid-ok")
    processor = EntryProcessor(deps)
    processor.process_signals(
        markets=[m1, m2],
        signals=[_mk_signal("cid-blocked"), _mk_signal("cid-ok")],
    )
    assert deps.executor.execute.call_count == 1


def test_process_signals_passes_to_executor_when_clean() -> None:
    deps = _mk_deps()
    processor = EntryProcessor(deps)
    processor.process_signals(markets=[_mk_market()], signals=[_mk_signal()])
    assert deps.executor.execute.call_count == 1


def test_process_signals_persists_position_and_trade_event() -> None:
    """SPEC-Z17: Successful fill → portfolio.add_position called + trade_event_log.append_entry called."""
    deps = _mk_deps()
    deps.state.portfolio.add_position.return_value = True
    processor = EntryProcessor(deps)
    processor.process_signals(markets=[_mk_market()], signals=[_mk_signal()])
    assert deps.state.portfolio.add_position.call_count == 1
    assert deps.trade_event_log.append_entry.call_count == 1
