"""factory.py mlb_submarket_engine injection için birim testler (SPEC-R Plan 1).

AgentDeps'in mlb_submarket_engine alanı:
  - enabled=False → None, sessiz
  - enabled=True  → MlbSubmarketEngine instance (Plan 4 T3), INFO loglanır
    (bkz. test_factory_mlb_real_engine.py tam test senaryoları için)
"""
from __future__ import annotations

import logging

from src.config.settings import AppConfig, MlbSubmarketConfig
from src.orchestration.agent import AgentDeps


def test_agent_deps_has_mlb_submarket_engine_field() -> None:
    """AgentDeps mlb_submarket_engine alanına sahip ve varsayılan None."""
    import dataclasses
    fields = {f.name: f for f in dataclasses.fields(AgentDeps)}
    assert "mlb_submarket_engine" in fields, (
        "AgentDeps.mlb_submarket_engine alanı tanımlı değil"
    )
    assert fields["mlb_submarket_engine"].default is None, (
        "mlb_submarket_engine varsayılan None olmalı"
    )


def test_factory_engine_none_when_disabled(tmp_path, monkeypatch) -> None:
    """mlb_submarket.enabled=False (default) → engine inject edilmez (None)."""
    from pathlib import Path
    from unittest.mock import MagicMock

    from src.orchestration.factory import build_agent
    from src.orchestration.startup import bootstrap

    cfg = AppConfig(mlb_submarket=MlbSubmarketConfig(enabled=False))
    state = bootstrap(cfg, logs_dir=tmp_path, trade_history_path=tmp_path / "t.jsonl")

    # Infrastructure mock'ları — build_agent production sınıflarını inşa eder
    monkeypatch.setattr(
        "src.orchestration.factory.GammaClient", lambda: MagicMock()
    )
    monkeypatch.setattr(
        "src.orchestration.factory.OddsAPIClient", lambda: MagicMock()
    )
    monkeypatch.setattr(
        "src.orchestration.factory.ESPNClient", lambda **kwargs: MagicMock()
    )
    monkeypatch.setattr(
        "src.orchestration.factory.PriceFeed",
        lambda **kw: MagicMock(),
    )

    agent = build_agent(state)
    assert agent.deps.mlb_submarket_engine is None


def test_factory_engine_info_logged_when_enabled(tmp_path, monkeypatch, caplog) -> None:
    """mlb_submarket.enabled=True → INFO logu (Plan 4 T3: gerçek engine inject edildi)."""
    from unittest.mock import MagicMock

    from src.orchestration.factory import build_agent
    from src.orchestration.startup import bootstrap

    cfg = AppConfig(mlb_submarket=MlbSubmarketConfig(
        enabled=True,
        rate_cache_path=str(tmp_path / "rate_cache.jsonl"),
    ))
    state = bootstrap(cfg, logs_dir=tmp_path, trade_history_path=tmp_path / "t.jsonl")

    monkeypatch.setattr("src.orchestration.factory.GammaClient", lambda: MagicMock())
    monkeypatch.setattr("src.orchestration.factory.OddsAPIClient", lambda: MagicMock())
    monkeypatch.setattr("src.orchestration.factory.ESPNClient", lambda **kwargs: MagicMock())
    monkeypatch.setattr(
        "src.orchestration.factory.PriceFeed", lambda **kw: MagicMock()
    )
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

    with caplog.at_level(logging.INFO, logger="src.orchestration.factory"):
        agent = build_agent(state)

    assert agent.deps.mlb_submarket_engine is not None, (
        "enabled=True olduğunda gerçek engine inject edilmeli"
    )
    assert any(
        "MlbSubmarketEngine initialized" in record.message
        and record.levelno == logging.INFO
        for record in caplog.records
    ), "enabled=True olduğunda INFO logu loglanmalı"
