"""End-to-end smoke test (SPEC-R Plan 1): mock MLB submarket engine →
scanner dispatch → process_signals → executor.execute → trade_logger.log.

Plan 1 closure: pipeline çalışıyor mu (real model olmadan)?
"""
from unittest.mock import MagicMock

from src.models.enums import Direction, EntryReason
from src.models.signal import Signal
from src.orchestration.entry_processor import EntryProcessor


def _make_signal(condition_id: str = "cid-mlb") -> Signal:
    return Signal(
        condition_id=condition_id,
        direction=Direction.BUY_YES,
        anchor_probability=0.62,
        market_price=0.55,
        edge=0.07,
        confidence="A",
        size_usdc=50.0,
        entry_reason=EntryReason.MLB_SUBMARKET,
        bookmaker_prob=0.0,
        num_bookmakers=0,
        has_sharp=False,
        sport_tag="baseball_mlb",
        event_id="evt-mlb",
    )


def _make_market(condition_id: str = "cid-mlb"):
    m = MagicMock()
    m.condition_id = condition_id
    m.event_id = "evt-mlb"
    m.question = "MLB total 8.5"
    m.liquidity = 100000.0
    m.yes_price = 0.55
    m.sport_tag = "baseball_mlb"
    m.sports_market_type = "totals"
    m.slug = "mlb-test-2026-05-21-total-8pt5"
    m.token_id = "tok-1"
    m.match_start_iso = ""
    m.end_date_iso = ""
    return m


def _make_deps():
    deps = MagicMock()
    deps.gate.config.max_positions = 50
    deps.gate.config.max_positions_per_event = 2
    deps.state.portfolio.count.return_value = 0
    deps.state.portfolio.count_event.return_value = 0
    deps.circuit_breaker.should_halt_entries.return_value = (False, "")
    deps.cooldown.is_active.return_value = False
    deps.cooldown.state.cooldown_remaining = 0
    deps.blacklist.is_blacklisted.return_value = False
    deps.executor.execute.return_value = MagicMock(
        filled=True, avg_price=0.55, size_usdc=50.0,
    )
    return deps


def test_mlb_submarket_signal_flows_end_to_end() -> None:
    """Mock engine → process_signals → executor.execute + portfolio.add_position + trade_logger.log."""
    market = _make_market()
    signal = _make_signal()
    deps = _make_deps()

    processor = EntryProcessor(deps)
    processor.process_signals(markets=[market], signals=[signal])

    deps.executor.execute.assert_called_once()
    assert deps.state.portfolio.add_position.call_count == 1
    assert deps.trade_logger.log.call_count == 1


def test_mlb_submarket_signal_skipped_when_event_cap_full() -> None:
    """Event_cap dolu → execute called değil."""
    deps = _make_deps()
    deps.state.portfolio.count_event.return_value = 2  # event cap full
    market = _make_market()
    signal = _make_signal()
    processor = EntryProcessor(deps)
    processor.process_signals(markets=[market], signals=[signal])
    deps.executor.execute.assert_not_called()
