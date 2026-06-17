from src.config.settings import load_config
from src.infrastructure.persistence.json_store import JsonStore
from src.orchestration.startup import bootstrap


def test_missing_file_defaults_not_paused(tmp_path):
    state = bootstrap(load_config(), logs_dir=tmp_path)
    assert state.trading_control.paused is False


def test_restores_paused_true(tmp_path):
    JsonStore(tmp_path / "trading_control.json").save({"paused": True})
    state = bootstrap(load_config(), logs_dir=tmp_path)
    assert state.trading_control.paused is True
