"""EntryGate + GateConfig stub sanity tests."""
from __future__ import annotations

import pytest
from src.strategy.entry.gate import EntryGate, GateConfig


def _make_cfg(**overrides) -> GateConfig:
    base = dict(
        min_favorite_probability=0.60,
        max_entry_price=0.80,
        max_positions=20,
        max_exposure_pct=0.50,
        confidence_bet_pct={"A": 0.05, "B": 0.04},
        max_single_bet_usdc=75.0,
        max_bet_pct=0.05,
        probability_weighted=True,
        min_bookmakers=15,
        min_sharps=3,
    )
    base.update(overrides)
    return GateConfig(**base)


def test_gate_config_defaults_hard_cap_overflow():
    cfg = _make_cfg()
    assert cfg.hard_cap_overflow_pct == 0.02


def test_gate_config_defaults_min_entry_size_pct():
    cfg = _make_cfg()
    assert cfg.min_entry_size_pct == 0.015


def test_gate_config_override_hard_cap_overflow():
    cfg = _make_cfg(hard_cap_overflow_pct=0.05)
    assert cfg.hard_cap_overflow_pct == 0.05


def test_gate_run_empty_markets_returns_empty():
    cfg = _make_cfg()
    gate = EntryGate(
        config=cfg,
        portfolio=None,
        circuit_breaker=None,
        cooldown=None,
        blacklist=None,
        odds_enricher=None,
        manipulation_checker=None,
    )
    assert gate.run([]) == []


def test_gate_run_nonempty_markets_returns_empty_stub():
    """Stub always returns [] — no entries until fully implemented."""
    from unittest.mock import MagicMock
    cfg = _make_cfg()
    gate = EntryGate(
        config=cfg,
        portfolio=None,
        circuit_breaker=None,
        cooldown=None,
        blacklist=None,
        odds_enricher=None,
        manipulation_checker=None,
    )
    fake_market = MagicMock()
    assert gate.run([fake_market]) == []


def test_gate_config_stored_on_entry_gate():
    cfg = _make_cfg()
    gate = EntryGate(
        config=cfg,
        portfolio=None,
        circuit_breaker=None,
        cooldown=None,
        blacklist=None,
        odds_enricher=None,
        manipulation_checker=None,
    )
    assert gate.config is cfg
    assert gate.config.max_positions == 20
