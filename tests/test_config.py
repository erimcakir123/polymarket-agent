import pytest
from pathlib import Path


def test_config_loads_from_yaml():
    from src.config import load_config
    config = load_config(Path("config.yaml"))
    assert config.mode == "dry_run"
    assert config.risk.kelly_fraction == 0.25
    assert config.risk.max_single_bet_usdc == 75
    assert config.edge.min_edge == 0.05
    assert config.cycle.default_interval_min == 30


def test_config_rejects_invalid_mode():
    from src.config import AppConfig
    with pytest.raises(Exception):
        AppConfig(mode="yolo")


def test_config_risk_constraints():
    from src.config import load_config
    config = load_config(Path("config.yaml"))
    assert 0 < config.risk.kelly_fraction <= 1.0
    assert config.risk.max_bet_pct <= 1.0
    assert config.risk.stop_loss_pct <= 1.0
