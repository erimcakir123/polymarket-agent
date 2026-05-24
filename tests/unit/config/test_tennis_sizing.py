"""Tennis sizing config tests (PLAN-SIZING-001, 2026-05-22).

Tennis lab paper trading sizing config:
- bankroll: $1000
- A non-bimodal: $50 (5% of $1000)
- B non-bimodal: $35 (3.5% of $1000)
- Bimodal piyasalar (set_totals + set_handicap): $15 cap (kullanıcı kayıp toleransı)
- max_bet $50 cap aktif (bankroll=2000 sanity test)
"""
from __future__ import annotations

from pathlib import Path

from src.config.settings import load_config
from src.domain.risk.position_sizer import confidence_position_size

TENNIS_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config_tennis.yaml"


def _load_tennis_config():
    return load_config(TENNIS_CONFIG_PATH)


def test_tennis_config_loads_initial_bankroll_1000() -> None:
    cfg = _load_tennis_config()
    assert cfg.initial_bankroll == 1000


def test_tennis_config_tier_a_bet_pct_5pct() -> None:
    cfg = _load_tennis_config()
    assert cfg.risk.confidence_bet_pct["A"] == 0.05


def test_tennis_config_tier_b_bet_pct_3pt5pct() -> None:
    cfg = _load_tennis_config()
    assert cfg.risk.confidence_bet_pct["B"] == 0.035


def test_tennis_config_max_bet_usdc_50() -> None:
    cfg = _load_tennis_config()
    assert cfg.risk.max_single_bet_usdc == 50


def test_tennis_config_max_bet_pct_5pct() -> None:
    cfg = _load_tennis_config()
    assert cfg.risk.max_bet_pct == 0.05


def test_tennis_config_set_totals_max_usdc_20() -> None:
    cfg = _load_tennis_config()
    assert cfg.risk.set_totals_max_usdc == 20


def test_tennis_config_set_handicap_max_usdc_20() -> None:
    cfg = _load_tennis_config()
    assert cfg.risk.set_handicap_max_usdc == 20


def test_tennis_config_max_positions_per_event_3() -> None:
    cfg = _load_tennis_config()
    assert cfg.risk.max_positions_per_event == 3


def test_tennis_sizing_tier_a_non_bimodal_produces_50_usdc() -> None:
    """Integration: bankroll=1000, A non-bimodal -> $50 (5% capped at $50)."""
    cfg = _load_tennis_config()
    size = confidence_position_size(
        confidence="A",
        bankroll=cfg.initial_bankroll,
        confidence_bet_pct=cfg.risk.confidence_bet_pct,
        max_bet_usdc=cfg.risk.max_single_bet_usdc,
        max_bet_pct=cfg.risk.max_bet_pct,
    )
    assert size == 50.0


def test_tennis_sizing_tier_b_non_bimodal_produces_35_usdc() -> None:
    """Integration: bankroll=1000, B non-bimodal -> $35 (3.5%)."""
    cfg = _load_tennis_config()
    size = confidence_position_size(
        confidence="B",
        bankroll=cfg.initial_bankroll,
        confidence_bet_pct=cfg.risk.confidence_bet_pct,
        max_bet_usdc=cfg.risk.max_single_bet_usdc,
        max_bet_pct=cfg.risk.max_bet_pct,
    )
    assert size == 35.0


def test_tennis_sizing_max_bet_cap_active_at_double_bankroll() -> None:
    """Sanity: bankroll=2000 -> A raw would be $100 but $50 cap clamps it."""
    cfg = _load_tennis_config()
    size = confidence_position_size(
        confidence="A",
        bankroll=2000,
        confidence_bet_pct=cfg.risk.confidence_bet_pct,
        max_bet_usdc=cfg.risk.max_single_bet_usdc,
        max_bet_pct=cfg.risk.max_bet_pct,
    )
    assert size == 50.0


def test_tennis_sizing_bimodal_cap_applies_a_tier() -> None:
    """A tier bimodal: bankroll=1000 raw $50 → $20 cap (set_totals_max_usdc)."""
    cfg = _load_tennis_config()
    size = confidence_position_size(
        confidence="A",
        bankroll=cfg.initial_bankroll,
        confidence_bet_pct=cfg.risk.confidence_bet_pct,
        max_bet_usdc=cfg.risk.set_totals_max_usdc,  # bimodal cap
        max_bet_pct=cfg.risk.max_bet_pct,
    )
    assert size == 20.0


def test_tennis_sizing_bimodal_cap_applies_b_tier() -> None:
    """B tier bimodal: bankroll=1000 raw $35 → $20 cap."""
    cfg = _load_tennis_config()
    size = confidence_position_size(
        confidence="B",
        bankroll=cfg.initial_bankroll,
        confidence_bet_pct=cfg.risk.confidence_bet_pct,
        max_bet_usdc=cfg.risk.set_handicap_max_usdc,  # bimodal cap
        max_bet_pct=cfg.risk.max_bet_pct,
    )
    assert size == 20.0
