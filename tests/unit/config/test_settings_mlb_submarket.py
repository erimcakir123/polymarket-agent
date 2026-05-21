from src.config.settings import MlbSubmarketConfig, AppConfig


def test_mlb_submarket_config_defaults() -> None:
    cfg = MlbSubmarketConfig()
    assert cfg.enabled is False
    assert cfg.min_edge == 0.05
    assert cfg.statsapi_timeout_sec == 10.0
    assert cfg.rate_cache_path == "data/mlb_rate_cache.jsonl"


def test_mlb_submarket_config_custom() -> None:
    cfg = MlbSubmarketConfig(enabled=True, min_edge=0.08)
    assert cfg.enabled is True
    assert cfg.min_edge == 0.08


def test_app_config_has_mlb_submarket_field() -> None:
    fields = AppConfig.model_fields
    assert "mlb_submarket" in fields


def test_min_edge_must_be_positive() -> None:
    import pytest
    with pytest.raises(Exception):
        MlbSubmarketConfig(min_edge=-0.01)
