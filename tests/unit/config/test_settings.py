"""settings.py için birim testler."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.config.settings import AppConfig, Mode, load_config


def test_load_config_missing_file_returns_defaults(tmp_path: Path) -> None:
    cfg = load_config(tmp_path / "nonexistent.yaml")
    assert isinstance(cfg, AppConfig)
    assert cfg.mode == Mode.DRY_RUN
    assert cfg.initial_bankroll == 1000.0
    assert cfg.edge.min_edge == 0.06


def test_load_config_valid_yaml_parses(tmp_path: Path) -> None:
    p = tmp_path / "cfg.yaml"
    p.write_text(
        "mode: paper\n"
        "initial_bankroll: 500.0\n"
        "edge:\n"
        "  min_edge: 0.08\n",
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.mode == Mode.PAPER
    assert cfg.initial_bankroll == 500.0
    assert cfg.edge.min_edge == 0.08


def test_load_config_invalid_mode_raises(tmp_path: Path) -> None:
    p = tmp_path / "cfg.yaml"
    p.write_text("mode: chaotic\n", encoding="utf-8")
    with pytest.raises(Exception):
        load_config(p)


def test_load_config_invalid_edge_value_raises(tmp_path: Path) -> None:
    p = tmp_path / "cfg.yaml"
    p.write_text("edge:\n  min_edge: high\n", encoding="utf-8")
    with pytest.raises(Exception):
        load_config(p)


def test_mode_enum_values() -> None:
    assert Mode.DRY_RUN.value == "dry_run"
    assert Mode.PAPER.value == "paper"
    assert Mode.LIVE.value == "live"


def test_config_a_conf_hold_defaults() -> None:
    cfg = AppConfig()
    assert cfg.a_conf_hold.market_flip_elapsed_gate == 0.85
    assert cfg.a_conf_hold.min_entry_price == 0.60
    assert cfg.a_conf_hold.market_flip_threshold == 0.50


def test_config_circuit_breaker_defaults() -> None:
    cfg = AppConfig()
    assert cfg.circuit_breaker.daily_max_loss_pct == -0.08
    assert cfg.circuit_breaker.hourly_max_loss_pct == -0.05
    assert cfg.circuit_breaker.consecutive_loss_limit == 4
    assert cfg.circuit_breaker.entry_block_threshold == -0.03


def test_config_scale_out_tiers_defaults() -> None:
    cfg = AppConfig()
    tiers = cfg.scale_out.tiers
    assert len(tiers) == 2
    assert tiers[0].threshold == 0.25
    assert tiers[0].sell_pct == 0.40
    assert tiers[1].threshold == 0.50
    assert tiers[1].sell_pct == 0.50


def test_repo_config_yaml_parses() -> None:
    """Kökdeki config.yaml geçerli Pydantic olarak yüklenmeli."""
    cfg = load_config()  # default Path("config.yaml")
    assert cfg.mode is not None
    assert cfg.initial_bankroll > 0
    assert cfg.edge.min_edge == 0.06
    # Gamma tag formatı (Odds API key değil)
    assert "nba" in cfg.scanner.allowed_sport_tags
    assert "nhl" in cfg.scanner.allowed_sport_tags
    assert "lpga*" in cfg.scanner.allowed_sport_tags
    # Draw-possible sporlar MVP dışı — eklenmemiş olmalı
    # Not: MMA/Boxing 2-outcome (draw yok) → MVP'ye dahil.
    for banned in ("soccer_epl", "soccer_laliga"):
        assert banned not in cfg.scanner.allowed_sport_tags, f"{banned} MVP dışı"
    # MMA + Boxing 2-outcome, eklenmiş olmalı
    assert "mma" in cfg.scanner.allowed_sport_tags
    assert "boxing" in cfg.scanner.allowed_sport_tags
    # Cricket (SPEC-011) — eklenmis olmali
    assert "cricket" in cfg.scanner.allowed_sport_tags
    assert "cricket_ipl" in cfg.scanner.allowed_sport_tags
