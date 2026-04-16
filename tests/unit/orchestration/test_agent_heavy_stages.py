"""Agent heavy cycle aşama snapshot'ları — scanning/analyzing/executing/idle."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.config.settings import AppConfig
from src.orchestration.agent import Agent, AgentDeps


def _make_deps() -> AgentDeps:
    """Mock'lu AgentDeps — heavy cycle çalıştırabilir minimal setup."""
    state = MagicMock()
    state.config = AppConfig()
    state.portfolio.positions = {}
    state.portfolio.count.return_value = 0
    state.portfolio.bankroll = 1000.0
    state.portfolio.total_invested.return_value = 0.0
    return AgentDeps(
        state=state,
        scanner=MagicMock(),
        cycle_manager=MagicMock(),
        executor=MagicMock(),
        odds_client=MagicMock(),
        trade_logger=MagicMock(),
        gate=MagicMock(),
        cooldown=MagicMock(),
        equity_logger=MagicMock(),
        skipped_logger=MagicMock(),
        stock=MagicMock(),
        bot_status_writer=MagicMock(),
        price_feed=None,
    )


def test_run_heavy_writes_scanning_then_analyzing_then_idle_when_no_signals():
    """Sinyalsiz pipeline: scanning → analyzing → idle; executing yazılmaz."""
    from src.models.market import MarketData

    deps = _make_deps()
    m = MarketData(
        condition_id="c", yes_token_id="y", no_token_id="n",
        question="Q", slug="s", sport_tag="mlb",
        yes_price=0.5, no_price=0.5, liquidity=1000.0, volume_24h=100.0,
        match_start_iso="2026-04-15T23:00:00Z", end_date_iso="",
        event_id="e", closed=False, resolved=False, accepting_orders=True,
    )
    deps.scanner.scan.return_value = [m]
    gate_result = MagicMock()
    gate_result.condition_id = "c"
    gate_result.signal = None
    gate_result.skipped_reason = "no_edge"
    deps.gate.run.return_value = [gate_result]
    deps.gate.config.max_exposure_pct = 0.30
    deps.gate.config.hard_cap_overflow_pct = 0.02
    deps.gate.config.min_entry_size_pct = 0.015
    deps.gate.config.max_positions = 50
    deps.stock.top_n_by_match_start.return_value = []
    deps.stock.has.return_value = False

    agent = Agent(deps)
    agent._entry.run_heavy()

    stages = [c.kwargs["stage"] for c in deps.bot_status_writer.write_stage.call_args_list]
    assert stages[0] == "scanning"
    assert "analyzing" in stages
    assert "idle" in stages
    assert "executing" not in stages


def test_run_heavy_writes_executing_when_signal_exists():
    """Sinyal üretilmişse executing aşaması yazılır."""
    from src.models.market import MarketData
    from src.models.signal import Signal
    from src.models.enums import Direction, EntryReason

    deps = _make_deps()
    market = MarketData(
        condition_id="cid",
        yes_token_id="y",
        no_token_id="n",
        question="A vs B",
        slug="a-vs-b",
        sport_tag="mlb",
        yes_price=0.5,
        no_price=0.5,
        liquidity=1000.0,
        volume_24h=100.0,
        match_start_iso="2026-04-15T23:00:00Z",
        end_date_iso="",
        event_id="e1",
        closed=False,
        resolved=False,
        accepting_orders=True,
    )
    signal = Signal(
        condition_id="cid",
        direction=Direction.BUY_YES,
        anchor_probability=0.6,
        market_price=0.5,
        edge=0.1,
        confidence="A",
        size_usdc=50.0,
        entry_reason=EntryReason.CONSENSUS,
        bookmaker_prob=0.6,
        num_bookmakers=3,
        has_sharp=True,
        sport_tag="mlb",
        event_id="e1",
    )
    gate_result = MagicMock()
    gate_result.condition_id = "cid"
    gate_result.signal = signal
    gate_result.skipped_reason = None
    deps.scanner.scan.return_value = [market]
    deps.gate.run.return_value = [gate_result]
    deps.gate.config.max_exposure_pct = 0.30
    deps.gate.config.hard_cap_overflow_pct = 0.02
    deps.gate.config.min_entry_size_pct = 0.015
    deps.gate.config.max_positions = 50
    deps.stock.top_n_by_match_start.return_value = []
    deps.stock.has.return_value = False
    deps.state.portfolio.positions = {}
    deps.state.portfolio.add_position.return_value = True
    deps.executor.place_order.return_value = {"status": "simulated", "price": 0.5}

    agent = Agent(deps)
    agent._entry.run_heavy()

    stages = [c.kwargs["stage"] for c in deps.bot_status_writer.write_stage.call_args_list]
    assert "executing" in stages


def test_run_heavy_idle_is_last():
    """idle her zaman en son yazılmalı (cycle sonu)."""
    deps = _make_deps()
    deps.scanner.scan.return_value = []
    deps.gate.run.return_value = []
    deps.gate.config.max_exposure_pct = 0.30
    deps.gate.config.hard_cap_overflow_pct = 0.02
    deps.gate.config.min_entry_size_pct = 0.015
    deps.gate.config.max_positions = 50
    deps.stock.top_n_by_match_start.return_value = []
    deps.stock.has.return_value = False

    agent = Agent(deps)
    agent._entry.run_heavy()

    stages = [c.kwargs["stage"] for c in deps.bot_status_writer.write_stage.call_args_list]
    assert stages[-1] == "idle"
