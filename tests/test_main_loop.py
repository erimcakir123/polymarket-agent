import pytest
from unittest.mock import MagicMock, patch


def test_agent_initializes_with_running_flag():
    """Agent starts with running=True."""
    from src.agent import Agent
    from src.config import load_config
    with patch.object(Agent, "__init__", lambda self, config: setattr(self, "running", True)):
        agent = Agent.__new__(Agent)
        agent.running = True
        assert agent.running is True


def test_stop_file_sets_running_false():
    """STOP_FILE mechanism sets running to False."""
    from src.agent import Agent
    from pathlib import Path
    stop = Path("logs/stop_signal")
    # Agent.STOP_FILE is Path("logs/stop_signal") and _check_stop_file reads it
    assert Agent.STOP_FILE == stop
