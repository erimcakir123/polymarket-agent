"""Agent scale-out branch — partial exit'te trade_logger.log_partial_exit çağrılmalı."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.config.settings import AppConfig
from src.domain.portfolio.manager import PortfolioManager
from src.models.enums import ExitReason
from src.models.position import Position
from src.orchestration.agent import Agent, AgentDeps
from src.orchestration.exit_processor import ExitProcessor
from src.strategy.exit.monitor import ExitSignal


def _make_deps_with_position():
    state = MagicMock()
    state.config = AppConfig()
    pos = Position(
        condition_id="cid",
        token_id="t",
        direction="BUY_YES",
        entry_price=0.5,
        size_usdc=100.0,
        shares=200.0,
        current_price=0.6,
        anchor_probability=0.5,
        entry_reason="consensus",
        confidence="A",
        sport_tag="mlb",
        event_id="e1",
        slug="a",
        entry_timestamp="2026-04-15T00:00:00Z",
    )
    state.portfolio.positions = {"cid": pos}
    state.portfolio.bankroll = 1000.0
    state.portfolio.add_position.return_value = True
    # 2026-05-30 fix: partial exit artık executor.partial_sell çağırır
    # (gerçek defter satımı). Mock FILLED dönmeli ki defter mantığı çalışsın.
    executor = MagicMock()
    executor.partial_sell.return_value = {
        "status": "FILLED",
        "mode": "dry_run",
        "filled_shares": 200.0 * 0.4,  # sell_pct=0.4 × shares=200
        "avg_price": 0.6,
        "reason": "scale_out",
    }
    return AgentDeps(
        state=state,
        scanner=MagicMock(),
        cycle_manager=MagicMock(),
        executor=executor,
        odds_client=MagicMock(),
        trade_logger=MagicMock(),
        gate=MagicMock(),
        cooldown=MagicMock(),
        equity_logger=MagicMock(),
        skipped_logger=MagicMock(),
        stock=MagicMock(),
        bot_status_writer=MagicMock(),
        price_feed=None,
    ), pos


def test_execute_partial_exit_calls_trade_logger_with_tier_and_pnl():
    """Scale-out partial exit'te trade_logger.log_partial_exit doğru argümanlarla çağrılır."""
    deps, pos = _make_deps_with_position()
    agent = Agent(deps)
    signal = ExitSignal(
        reason=ExitReason.SCALE_OUT,
        partial=True,
        sell_pct=0.4,
        tier=1,
    )
    agent._exit._execute_exit(pos, signal)

    assert deps.trade_logger.log_partial_exit.called
    kwargs = deps.trade_logger.log_partial_exit.call_args.kwargs
    assert kwargs["condition_id"] == "cid"
    assert kwargs["tier"] == 1
    assert kwargs["sell_pct"] == 0.4
    # pos.unrealized_pnl_usdc * 0.4 — pozisyon entry 0.5, current 0.6, shares 200
    # unrealized = 200 * 0.6 - 100 = 20; partial = 20 * 0.4 = 8.0
    assert abs(kwargs["realized_pnl_usdc"] - 8.0) < 0.01
    assert "timestamp" in kwargs


def test_execute_partial_exit_does_not_call_remove_position():
    """Partial exit pozisyonu silmemeli."""
    deps, pos = _make_deps_with_position()
    agent = Agent(deps)
    signal = ExitSignal(
        reason=ExitReason.SCALE_OUT,
        partial=True,
        sell_pct=0.4,
        tier=1,
    )
    agent._exit._execute_exit(pos, signal)

    assert not deps.state.portfolio.remove_position.called
    assert deps.state.portfolio.apply_partial_exit.called


def test_partial_exit_rollback_on_race():
    """Pozisyon ara silinmişse mutation rollback edilir (SPEC-A2)."""
    deps, pos = _make_deps_with_position()
    # Replace portfolio with REAL empty PortfolioManager — apply_partial_exit raises ValueError
    deps.state.portfolio = PortfolioManager(initial_bankroll=1000.0)
    # NOT: pos portfolio'da yok ama exit_processor pos referansını kullanır

    ep = ExitProcessor(deps)
    signal = ExitSignal(
        reason=ExitReason.SCALE_OUT,
        partial=True,
        sell_pct=0.4,
        tier=1,
    )

    shares_before = pos.shares
    size_before = pos.size_usdc
    realized_before = pos.scale_out_realized_usdc

    ep._execute_partial_exit(pos, signal)

    # Mutation rollback edildi (pozisyon eski haline döndü)
    assert pos.shares == pytest.approx(shares_before)
    assert pos.size_usdc == pytest.approx(size_before)
    assert pos.scale_out_realized_usdc == pytest.approx(realized_before)
    # trade_logger çağrılmadı (rollback'ten sonra return)
    assert not deps.trade_logger.log_partial_exit.called
