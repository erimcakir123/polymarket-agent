"""entry_processor.py skip_detail wiring tests (SPEC-001)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from src.domain.portfolio.manager import PortfolioManager
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
            max_positions_per_event=3,
            max_exposure_pct=0.5,
        )
    if portfolio_positions is None:
        portfolio_positions = {}

    portfolio = MagicMock()
    portfolio.bankroll = bankroll
    portfolio.realized_pnl = 0.0
    portfolio.positions = portfolio_positions
    portfolio.count.return_value = len(portfolio_positions)
    portfolio.count_event.return_value = 0
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


def test_process_markets_exposure_cap_logs_detail_with_invested_cap():
    """SPEC-P: Entry_processor's exposure cap re-check (batch race) logs invested/cap detail."""
    signal = _make_signal()
    gate_result = GateResult(
        condition_id="0x1",
        signal=signal,
        skipped_reason="",
        skip_detail="",
    )

    # Tight cap: %1 of (bankroll + invested = $1015) ≈ $10.15.
    # Mevcut invested $15 ≥ $10.15 → at_or_over_cap True → blok.
    gate_config = SimpleNamespace(
        max_positions=50,
        max_positions_per_event=3,
        max_exposure_pct=0.01,
    )

    existing_pos = MagicMock()
    existing_pos.size_usdc = 15.0

    deps = _make_deps(
        gate_config=gate_config,
        bankroll=1000.0,
        portfolio_positions={"existing_pos_id": existing_pos},
    )
    deps.state.portfolio.total_invested.return_value = 15.0
    deps.gate.run.return_value = [gate_result]

    processor = EntryProcessor(deps)
    processor.process_markets([_make_market()])

    calls = deps.skipped_logger.log.call_args_list
    found = False
    for call in calls:
        record = call[0][0]
        if (record.skip_reason == "exposure_cap_reached"
            and "invested=" in record.skip_detail
            and "cap=" in record.skip_detail):
            found = True
    assert found, (
        f"Expected exposure_cap_reached skip with structured detail "
        f"(invested=X.XX, cap=X.XX). "
        f"Got: {[(c[0][0].skip_reason, c[0][0].skip_detail) for c in calls]}"
    )


def test_entry_processor_enforces_max_positions_per_event_in_batch():
    """Batch entry race condition (Pistons-Cavaliers bug):

    Gate evaluates `count_event` BEFORE any add_position fires, so 4 markets
    of the same event can all pass the gate in a single cycle. Without the
    per-iteration check inside the for-loop, all 4 would open — violating
    max_positions_per_event=3 (2026-05-22 cap artırımı).

    Setup: 4 markets, same event_id="465162", all approved by gate.
    Expected: only 3 positions open; the 4th skipped with
              reason='event_count_per_event_cap' and re-added to stock.
    """
    event_id = "465162"
    # 4 same-event markets, distinct condition_ids
    markets = [
        _make_market(slug=f"nba-det-cle-m{i}", cid=f"0x{i}") for i in range(1, 5)
    ]
    for m in markets:
        m.event_id = event_id  # all same event

    # Gate approves all 4 (the bug: no per-iteration enforcement after this)
    gate_results = [
        GateResult(condition_id=f"0x{i}", signal=_make_signal(cid=f"0x{i}"),
                   skipped_reason="", skip_detail="")
        for i in range(1, 5)
    ]

    # Real PortfolioManager so count_event reflects live state mid-batch
    portfolio = PortfolioManager(initial_bankroll=1000.0)

    gate_config = SimpleNamespace(
        max_positions=50,
        max_positions_per_event=3,
        max_exposure_pct=0.5,
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
    deps.gate.run.return_value = gate_results
    # executor fill — simulated, returns the price/size we'd realistically get
    deps.executor.place_order.return_value = {
        "status": "simulated", "price": 0.55,
    }

    processor = EntryProcessor(deps)
    processor.process_markets(markets)

    # Core assertion: exactly 3 positions open for this event, NOT 4
    assert portfolio.count_event(event_id) == 3, (
        f"Expected 3 positions for event_id={event_id} (cap=3), "
        f"got {portfolio.count_event(event_id)}. "
        f"Batch race condition NOT prevented."
    )

    # The 4th market must be skipped with the dedicated reason
    skip_calls = deps.skipped_logger.log.call_args_list
    cap_skip_found = False
    for call in skip_calls:
        record = call[0][0]
        if record.skip_reason == "event_count_per_event_cap":
            cap_skip_found = True
            assert event_id in record.skip_detail
            assert "3/3" in record.skip_detail
    assert cap_skip_found, (
        "Expected a 'event_count_per_event_cap' skip log for the 4th market. "
        f"Got: {[c[0][0].skip_reason for c in skip_calls]}"
    )

    # The 4th market should also be re-queued in stock with the cap reason
    stock_add_calls = deps.stock.add.call_args_list
    cap_stock_found = any(
        len(c[0]) >= 2 and c[0][1] == "event_count_per_event_cap"
        for c in stock_add_calls
    )
    assert cap_stock_found, (
        "Expected stock.add(market, 'event_count_per_event_cap') for skipped 4th market."
    )


def test_run_heavy_dispatches_model_signals_when_engine_present() -> None:
    """Heavy cycle: engine present → collect_model_signals → process_signals called."""
    from unittest.mock import MagicMock, patch
    from src.orchestration.entry_processor import EntryProcessor

    # Build deps with a mock engine that returns a Signal for the MLB totals market
    deps = MagicMock()
    mlb_market = MagicMock()
    mlb_market.condition_id = "cid-mlb"
    mlb_market.sport_tag = "baseball_mlb"
    mlb_market.sports_market_type = "totals"

    nba_market = MagicMock()
    nba_market.condition_id = "cid-nba"
    nba_market.sport_tag = "basketball_nba"
    nba_market.sports_market_type = "moneyline"

    deps.scanner.scan.return_value = [mlb_market, nba_market]
    deps.stock.refresh_from_scan.return_value = None
    deps.stock.evict_expired.return_value = None
    deps.stock.has.return_value = False
    deps.stock.top_n_by_match_start.return_value = []
    deps.stock.config.jit_batch_multiplier = 2
    deps.state.portfolio.count.return_value = 0
    deps.state.portfolio.positions = {}
    deps.gate.config.max_positions = 50
    deps.bot_status_writer.write_stage.return_value = None

    # Mock engine returns a signal for MLB only
    fake_signal = MagicMock()
    fake_signal.condition_id = "cid-mlb"
    deps.mlb_submarket_engine = MagicMock()
    deps.mlb_submarket_engine.process.return_value = fake_signal

    processor = EntryProcessor(deps)
    with patch.object(processor, "process_signals") as mock_ps, \
         patch.object(processor, "process_markets"):
        processor.run_heavy()

    # process_signals should be called once with the MLB market only
    assert mock_ps.call_count == 1
    call = mock_ps.call_args
    # kwargs-first, fall back to positional
    markets_arg: list = call.kwargs["markets"] if call.kwargs and "markets" in call.kwargs else list(call.args[0])
    assert len(markets_arg) == 1
    assert markets_arg[0].condition_id == "cid-mlb"


def test_run_heavy_skips_process_signals_when_engine_none() -> None:
    """Heavy cycle: engine=None → process_signals NOT called."""
    from unittest.mock import MagicMock, patch
    from src.orchestration.entry_processor import EntryProcessor

    deps = MagicMock()
    mlb_market = MagicMock()
    mlb_market.condition_id = "cid-mlb"
    mlb_market.sport_tag = "baseball_mlb"
    mlb_market.sports_market_type = "totals"

    deps.scanner.scan.return_value = [mlb_market]
    deps.stock.refresh_from_scan.return_value = None
    deps.stock.evict_expired.return_value = None
    deps.stock.has.return_value = False
    deps.stock.top_n_by_match_start.return_value = []
    deps.stock.config.jit_batch_multiplier = 2
    deps.state.portfolio.count.return_value = 0
    deps.state.portfolio.positions = {}
    deps.gate.config.max_positions = 50
    deps.bot_status_writer.write_stage.return_value = None
    deps.mlb_submarket_engine = None

    processor = EntryProcessor(deps)
    with patch.object(processor, "process_signals") as mock_ps, \
         patch.object(processor, "process_markets"):
        processor.run_heavy()

    mock_ps.assert_not_called()
