"""Tennis sizing config tests (Stage 3 PLAN-TENNIS-001).

User-approved values for tennis paper trading:
- bankroll: $500
- max bet: $50
- A tier -> $50 (10% of bankroll)
- B tier -> $40 (8% of bankroll)
- max_bet $50 cap is active (bankroll=1000 sanity test).
"""
from __future__ import annotations

from pathlib import Path

from src.config.settings import load_config
from src.domain.risk.position_sizer import confidence_position_size

TENNIS_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config_tennis.yaml"


def _load_tennis_config():
    return load_config(TENNIS_CONFIG_PATH)


def test_tennis_config_loads_initial_bankroll_500() -> None:
    cfg = _load_tennis_config()
    assert cfg.initial_bankroll == 500


def test_tennis_config_tier_a_bet_pct_10pct() -> None:
    cfg = _load_tennis_config()
    assert cfg.risk.confidence_bet_pct["A"] == 0.10


def test_tennis_config_tier_b_bet_pct_8pct() -> None:
    cfg = _load_tennis_config()
    assert cfg.risk.confidence_bet_pct["B"] == 0.08


def test_tennis_config_max_bet_usdc_50() -> None:
    cfg = _load_tennis_config()
    assert cfg.risk.max_single_bet_usdc == 50


def test_tennis_config_max_bet_pct_10pct() -> None:
    cfg = _load_tennis_config()
    assert cfg.risk.max_bet_pct == 0.10


def test_tennis_sizing_tier_a_produces_50_usdc() -> None:
    """Integration: bankroll=500 with tennis config -> A tier = $50."""
    cfg = _load_tennis_config()
    size = confidence_position_size(
        confidence="A",
        bankroll=cfg.initial_bankroll,
        confidence_bet_pct=cfg.risk.confidence_bet_pct,
        max_bet_usdc=cfg.risk.max_single_bet_usdc,
        max_bet_pct=cfg.risk.max_bet_pct,
    )
    assert size == 50.0


def test_tennis_sizing_tier_b_produces_40_usdc() -> None:
    """Integration: bankroll=500 with tennis config -> B tier = $40."""
    cfg = _load_tennis_config()
    size = confidence_position_size(
        confidence="B",
        bankroll=cfg.initial_bankroll,
        confidence_bet_pct=cfg.risk.confidence_bet_pct,
        max_bet_usdc=cfg.risk.max_single_bet_usdc,
        max_bet_pct=cfg.risk.max_bet_pct,
    )
    assert size == 40.0


def test_tennis_sizing_max_bet_cap_active_at_double_bankroll() -> None:
    """Sanity: bankroll=1000 -> A tier raw would be $100 but $50 cap clamps it."""
    cfg = _load_tennis_config()
    size = confidence_position_size(
        confidence="A",
        bankroll=1000,
        confidence_bet_pct=cfg.risk.confidence_bet_pct,
        max_bet_usdc=cfg.risk.max_single_bet_usdc,
        max_bet_pct=cfg.risk.max_bet_pct,
    )
    assert size == 50.0
