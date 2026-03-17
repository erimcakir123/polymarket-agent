import pytest
from unittest.mock import MagicMock, patch


def test_single_cycle_dry_run():
    from src.main import Agent
    from src.config import load_config
    config = load_config()
    agent = Agent(config)
    agent.scanner = MagicMock()
    agent.scanner.fetch.return_value = []
    agent.wallet = MagicMock()
    agent.wallet.get_usdc_balance.return_value = 60.0
    agent.news_scanner = MagicMock()
    agent.news_scanner.fetch_headlines.return_value = []
    agent.run_cycle()
    agent.scanner.fetch.assert_called_once()


def test_graceful_shutdown_flag():
    from src.main import Agent
    from src.config import load_config
    config = load_config()
    agent = Agent(config)
    assert agent.running is True
    agent.shutdown()
    assert agent.running is False
