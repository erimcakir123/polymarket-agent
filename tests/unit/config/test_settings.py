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


def test_config_agent_defaults() -> None:
    cfg = AppConfig()
    assert cfg.agent.cycle_max_consecutive_errors == 2


def test_config_scale_out_tiers_defaults() -> None:
    cfg = AppConfig()
    tiers = cfg.scale_out.tiers
    assert len(tiers) == 2
    assert tiers[0].threshold == 0.25
    assert tiers[0].sell_pct == 0.40
    assert tiers[1].threshold == 0.50
    assert tiers[1].sell_pct == 0.50


def test_config_score_defaults() -> None:
    cfg = AppConfig()
    assert cfg.score.enabled is True
    assert cfg.score.poll_normal_sec == 60
    assert cfg.score.poll_critical_sec == 30
    assert cfg.score.critical_price_threshold == 0.35


def test_config_score_disabled_overrides() -> None:
    cfg = AppConfig(score={"enabled": False, "poll_normal_sec": 60, "poll_critical_sec": 30, "critical_price_threshold": 0.35})
    assert cfg.score.enabled is False


def test_repo_config_yaml_parses() -> None:
    """Kökdeki config.yaml geçerli Pydantic olarak yüklenmeli."""
    cfg = load_config()  # default Path("config.yaml")
    assert cfg.mode is not None
    assert cfg.initial_bankroll > 0
    assert cfg.edge.min_edge == 0.06
    # 2026-05-11: Basketball-only — tek olay swing düşük (sayı = %1-3 fiyat etkisi).
    # Diğer sportlar (NHL/MLB/Tennis/Soccer/Football/Golf/Combat) tek olayda fiyatı
    # %20-100 uçuruyor → bot stop-loss tutamıyor; kapatıldı.
    for must_have in ("nba", "wnba", "ncaab", "cbb", "wncaab", "euroleague", "nbl"):
        assert must_have in cfg.scanner.allowed_sport_tags, f"{must_have} basketball-only listede olmalı"
    # Draw-possible sporlar MVP dışı — eklenmemiş olmalı
    for banned in ("soccer_epl", "soccer_laliga", "cricket"):
        assert banned not in cfg.scanner.allowed_sport_tags, f"{banned} MVP dışı"
    # 2026-05-11 brutal daraltma: bu sportlar yapısal yüksek-swing → kapatıldı
    for high_swing in ("nhl", "mlb", "kbo", "baseball", "ncaaf", "cfl", "ufl", "lpga*", "liv*", "pga*"):
        assert high_swing not in cfg.scanner.allowed_sport_tags, f"{high_swing} yüksek-swing — kapatıldı 2026-05-11"
    # Combat sports kaldırıldı 2026-05-10 (SPEC-J) — canlı skor yok, KO/karar bazlı reaksiyon imkansız
    for combat in ("mma", "ufc", "boxing"):
        assert combat not in cfg.scanner.allowed_sport_tags, f"{combat} SPEC-J ile kaldırıldı"
