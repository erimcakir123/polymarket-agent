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


import yaml
from pathlib import Path


def test_root_config_yaml_mlb_submarket_block_valid() -> None:
    """config.yaml yüklendiğinde mlb_submarket bloğu geçerli (enabled değeri
    operasyonel karar — SPEC-R aktivasyonu sonrası True/False değişebilir)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "config.yaml"
        if candidate.exists():
            root_cfg = candidate
            break
    else:
        raise AssertionError("config.yaml not found")
    data = yaml.safe_load(root_cfg.read_text(encoding="utf-8"))
    cfg = AppConfig(**data)
    assert isinstance(cfg.mlb_submarket.enabled, bool)
    assert cfg.mlb_submarket.min_edge > 0
