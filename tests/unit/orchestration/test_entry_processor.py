"""entry_processor.py skip_detail wiring tests (SPEC-001)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from src.models.market import MarketData
from src.models.signal import Signal
from src.orchestration.entry_processor import EntryProcessor
from src.strategy.entry.gate import GateResult


def _make_market(slug="nba-lal-bos-2026-04-13", cid="0x1"):
    return MarketData(
        condition_id=cid,
        slug=slug,
        question="Will Lakers beat Celtics?",
        sport_tag="basketball/nba",
        yes_token_id="y",
        no_token_id="n",
        yes_price=0.55,
        no_price=0.45,
        liquidity=50000,
        volume_24h=10000,
        tags=[],
        end_date_iso="2026-04-14T00:00:00Z",
        event_id="e123",
        match_start_iso="2026-04-14T00:00:00Z",
        closed=False,
        resolved=False,
        accepting_orders=True,
    )


def _make_signal(cid="0x1"):
    """Build a valid Signal for entry_processor."""
    return Signal(
        condition_id=cid,
        direction="BUY_YES",
        market_price=0.55,
        anchor_probability=0.65,
        edge=0.08,
        bookmaker_prob=0.65,
        num_bookmakers=3.0,
        has_sharp=True,
        confidence="B",
        entry_reason="normal",
        size_usdc=20.0,
    )


def _make_deps(gate_config=None, bankroll=1000.0, portfolio_positions=None):
    """Build minimal deps object for EntryProcessor."""
    if gate_config is None:
        gate_config = SimpleNamespace(
            max_positions=50,
            max_exposure_pct=0.5,
            hard_cap_overflow_pct=0.02,
            min_entry_size_pct=0.015,
        )
    if portfolio_positions is None:
        portfolio_positions = {}

    portfolio = MagicMock()
    portfolio.bankroll = bankroll
    portfolio.realized_pnl = 0.0
    portfolio.positions = portfolio_positions
    portfolio.count.return_value = len(portfolio_positions)
    portfolio.total_invested.return_value = sum(
        p.size_usdc for p in portfolio_positions.values() if hasattr(p, "size_usdc")
    )

    deps = SimpleNamespace(
        state=SimpleNamespace(
            config=SimpleNamespace(mode=SimpleNamespace(value="dry_run")),
            portfolio=portfolio,
        ),
        scanner=MagicMock(),
        stock=MagicMock(),
        gate=MagicMock(),
        skipped_logger=MagicMock(),
        bot_status_writer=MagicMock(),
        equity_logger=MagicMock(),
        executor=MagicMock(),
        trade_logger=MagicMock(),
        price_feed=None,
    )
    deps.gate.config = gate_config
    return deps


def test_process_markets_gate_skip_passes_detail_through():
    """Gate skip's skip_detail should be passed through to log_skip."""
    # Gate returns a skip with detail set
    gate_result = GateResult(
        condition_id="0x1",
        signal=None,
        skipped_reason="no_edge",
        skip_detail="edge=0.042, min=0.06",
    )

    deps = _make_deps()
    deps.gate.run.return_value = [gate_result]

    processor = EntryProcessor(deps)
    processor.process_markets([_make_market()])

    # log_skip should have been called with detail
    assert deps.skipped_logger.log.called
    calls = deps.skipped_logger.log.call_args_list
    found = False
    for call in calls:
        record = call[0][0]
        if (record.skip_reason == "no_edge"
            and record.skip_detail == "edge=0.042, min=0.06"):
            found = True
    assert found, (
        f"Expected skip_reason=no_edge with skip_detail='edge=0.042, min=0.06'. "
        f"Got: {[(c[0][0].skip_reason, c[0][0].skip_detail) for c in calls]}"
    )


def test_process_markets_exposure_cap_logs_detail_with_available_min():
    """Entry_processor's own exposure cap skip should log structured detail."""
    signal = _make_signal()
    gate_result = GateResult(
        condition_id="0x1",
        signal=signal,
        skipped_reason="",
        skip_detail="",
    )

    gate_config = SimpleNamespace(
        max_positions=50,
        max_exposure_pct=0.01,  # tight cap: 1% of 1000 = $10
        hard_cap_overflow_pct=0.0,
        min_entry_size_pct=0.015,  # min size = 1000 * 0.015 = $15
    )

    # Portfolio has $9.2 invested, so available = $10 - $9.2 = $0.8
    # min_size = $15, so available < min_size → exposure_cap_reached
    existing_pos = MagicMock()
    existing_pos.size_usdc = 9.2

    deps = _make_deps(
        gate_config=gate_config,
        bankroll=1000.0,
        portfolio_positions={"existing_pos_id": existing_pos},
    )
    deps.state.portfolio.total_invested.return_value = 9.2
    deps.gate.run.return_value = [gate_result]

    processor = EntryProcessor(deps)
    processor.process_markets([_make_market()])

    # log_skip should have been called for exposure_cap_reached with detail
    calls = deps.skipped_logger.log.call_args_list
    found = False
    for call in calls:
        record = call[0][0]
        if (record.skip_reason == "exposure_cap_reached"
            and "available=" in record.skip_detail
            and "min=" in record.skip_detail):
            found = True
    assert found, (
        f"Expected exposure_cap_reached skip with structured detail "
        f"(available=X.XX, min=X.XX). "
        f"Got: {[(c[0][0].skip_reason, c[0][0].skip_detail) for c in calls]}"
    )
