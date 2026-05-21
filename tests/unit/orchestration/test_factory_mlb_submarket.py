"""factory.py mlb_submarket_engine injection için birim testler (SPEC-R Plan 1).

AgentDeps'in mlb_submarket_engine alanı:
  - enabled=False → None, sessiz
  - enabled=True  → hâlâ None (Plan 4 placeholder), WARNING loglanır
"""
from __future__ import annotations

import logging

from src.config.settings import AppConfig, MlbSubmarketConfig
from src.orchestration.agent import AgentDeps
from src.strategy.entry.mlb_submarket_engine_protocol import MlbSubmarketEngineProtocol


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
        "src.orchestration.factory.ESPNClient", lambda: MagicMock()
    )
    monkeypatch.setattr(
        "src.orchestration.factory.PriceFeed",
        lambda max_spike_pct: MagicMock(),
    )

    agent = build_agent(state)
    assert agent.deps.mlb_submarket_engine is None


def test_factory_engine_none_when_enabled_no_impl_yet(tmp_path, monkeypatch, caplog) -> None:
    """mlb_submarket.enabled=True (Plan 4 placeholder) → still None, WARNING loglanır."""
    from unittest.mock import MagicMock

    from src.orchestration.factory import build_agent
    from src.orchestration.startup import bootstrap

    cfg = AppConfig(mlb_submarket=MlbSubmarketConfig(enabled=True))
    state = bootstrap(cfg, logs_dir=tmp_path, trade_history_path=tmp_path / "t.jsonl")

    monkeypatch.setattr(
        "src.orchestration.factory.GammaClient", lambda: MagicMock()
    )
    monkeypatch.setattr(
        "src.orchestration.factory.OddsAPIClient", lambda: MagicMock()
    )
    monkeypatch.setattr(
        "src.orchestration.factory.ESPNClient", lambda: MagicMock()
    )
    monkeypatch.setattr(
        "src.orchestration.factory.PriceFeed",
        lambda max_spike_pct: MagicMock(),
    )

    with caplog.at_level(logging.WARNING, logger="src.orchestration.factory"):
        agent = build_agent(state)

    assert agent.deps.mlb_submarket_engine is None
    assert any(
        "Plan 4" in record.message and record.levelno == logging.WARNING
        for record in caplog.records
    ), "enabled=True olduğunda Plan 4 placeholder WARNING loglanmalı"
