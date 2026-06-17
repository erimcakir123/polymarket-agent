from unittest.mock import MagicMock

from src.domain.control.trading_control import TradingControl
from src.orchestration.agent import Agent


def _agent():
    deps = MagicMock()
    deps.state.trading_control = TradingControl()
    deps.price_feed = None
    deps.notifier = MagicMock()
    deps.state.config.mode.value = "paper"
    deps.state.portfolio.count.return_value = 3
    deps.state.portfolio.realized_pnl = 12.5
    deps.state.portfolio.bankroll = 980.0
    return Agent(deps), deps


def test_request_pause_sets_flag_and_persists():
    agent, deps = _agent()
    agent.request_pause()
    assert deps.state.trading_control.paused is True
    deps.state.trading_control_store.save.assert_called_once()


def test_request_resume_clears_flag_and_persists():
    agent, deps = _agent()
    deps.state.trading_control.pause()
    agent.request_resume()
    assert deps.state.trading_control.paused is False
    deps.state.trading_control_store.save.assert_called_once()


def test_status_summary_contains_key_fields():
    agent, _ = _agent()
    text = agent.status_summary()
    assert "paper" in text.lower()
    assert "3" in text          # pozisyon sayısı
    assert "12.5" in text       # realized pnl
