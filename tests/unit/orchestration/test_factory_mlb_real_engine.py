"""factory.py — gerçek MlbSubmarketEngine injection testleri (SPEC-R Plan 4 T3).

enabled=True → MlbSubmarketEngine instance (Plan 4'te eklendi).
enabled=False → None (Plan 1 davranışı korunur).
"""
from __future__ import annotations

from unittest.mock import MagicMock

from src.config.settings import AppConfig, MlbSubmarketConfig
from src.strategy.entry.mlb_submarket_engine import MlbSubmarketEngine


def _build_state(cfg: AppConfig, tmp_path):
    from src.orchestration.startup import bootstrap
    return bootstrap(cfg, logs_dir=tmp_path, trade_history_path=tmp_path / "t.jsonl")


def _mock_infra(monkeypatch) -> None:
    """Mock infrastructure clients factory'nin üst düzey import'larını bypass eder."""
    monkeypatch.setattr("src.orchestration.factory.GammaClient", lambda: MagicMock())
    monkeypatch.setattr("src.orchestration.factory.OddsAPIClient", lambda: MagicMock())
    monkeypatch.setattr("src.orchestration.factory.ESPNClient", lambda: MagicMock())
    monkeypatch.setattr(
        "src.orchestration.factory.PriceFeed",
        lambda max_spike_pct: MagicMock(),
    )


def test_factory_returns_real_engine_when_enabled(monkeypatch, tmp_path) -> None:
    """enabled=True → deps.mlb_submarket_engine gerçek MlbSubmarketEngine instance'ı."""
    from src.orchestration.factory import build_agent

    cfg = AppConfig(
        mlb_submarket=MlbSubmarketConfig(
            enabled=True,
            min_edge=0.05,
            rate_cache_path=str(tmp_path / "rate_cache.jsonl"),
        )
    )
    state = _build_state(cfg, tmp_path)
    _mock_infra(monkeypatch)

    # MLB infra client'larını source modüllerinde mock'la (lazy import nedeniyle).
    monkeypatch.setattr(
        "src.infrastructure.mlb_data.statsapi_client.StatsApiClient",
        lambda timeout=10.0, **kw: MagicMock(),
    )
    monkeypatch.setattr(
        "src.infrastructure.mlb_data.statcast_client.StatcastClient",
        lambda cache_dir=None: MagicMock(),
    )
    monkeypatch.setattr(
        "src.infrastructure.mlb_data.weather_client.WeatherClient",
        lambda: MagicMock(),
    )
    monkeypatch.setattr(
        "src.infrastructure.mlb_data.rate_cache.RateCache",
        lambda path: MagicMock(),
    )

    agent = build_agent(state)
    assert agent.deps.mlb_submarket_engine is not None
    assert isinstance(agent.deps.mlb_submarket_engine, MlbSubmarketEngine)


def test_factory_engine_none_when_disabled(monkeypatch, tmp_path) -> None:
    """Plan 1 davranışı korunur: enabled=False → None, sessiz."""
    from src.orchestration.factory import build_agent

    cfg = AppConfig(mlb_submarket=MlbSubmarketConfig(enabled=False))
    state = _build_state(cfg, tmp_path)
    _mock_infra(monkeypatch)

    agent = build_agent(state)
    assert agent.deps.mlb_submarket_engine is None
