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
    assert tiers[0].threshold == 0.40
    assert tiers[0].sell_pct == 0.40
    assert tiers[1].threshold == 0.70
    assert tiers[1].sell_pct == 0.50


def test_scale_out_default_tiers_are_distance_based() -> None:
    from src.config.settings import ScaleOutConfig
    cfg = ScaleOutConfig()
    assert len(cfg.tiers) == 2
    assert cfg.tiers[0].threshold == 0.40
    assert cfg.tiers[0].sell_pct == 0.40
    assert cfg.tiers[1].threshold == 0.70
    assert cfg.tiers[1].sell_pct == 0.50


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
    # 2026-05-15 iyi-donem-rollback: 19 Apr peak sport portföyü geri açıldı.
    # Hockey için SADECE NHL (kullanıcı kararı — AHL/Liiga/SHL/Mestis/Allsvenskan EKLENMEZ).
    for must_have in (
        "mlb", "milb", "npb", "kbo", "baseball",
        "nba", "wnba", "ncaab", "wncaab", "cbb", "euroleague", "nbl",
        "nhl",
        "ncaaf", "cfl", "ufl",
        "tennis", "atp*", "wta*",
        "mma", "ufc", "boxing",
        "lpga*", "liv*", "pga*",
    ):
        assert must_have in cfg.scanner.allowed_sport_tags, f"{must_have} listede olmalı"
    # Draw-possible sporlar MVP dışı — eklenmemiş olmalı
    for banned in ("soccer_epl", "soccer_laliga"):
        assert banned not in cfg.scanner.allowed_sport_tags, f"{banned} MVP dışı"
    # Hockey alt ligleri (NHL hariç) — kullanıcı kararı ile EKLENMEZ
    for hockey_minor in ("ahl", "liiga", "mestis", "shl", "allsvenskan"):
        assert hockey_minor not in cfg.scanner.allowed_sport_tags, (
            f"{hockey_minor} eklenmez — kullanıcı kararı (sadece NHL)"
        )


def test_force_close_timeouts_loads_from_yaml(tmp_path: Path) -> None:
    import yaml
    cfg_dict = {
        "initial_bankroll": 1000,
        "scan_interval_seconds": 60,
        "max_active_markets": 30,
        "edge": {"min_edge": 0.05, "min_market_volume": 100},
        "risk": {
            "max_single_bet_usdc": 50,
            "max_bet_pct": 0.05,
            "confidence_bet_pct": {"A": 0.05, "B": 0.035},
            "force_close_timeouts": {
                "tennis_first_set_winner": 60,
                "default": 300,
            },
        },
    }
    cfg_path = tmp_path / "test_config.yaml"
    cfg_path.write_text(yaml.dump(cfg_dict), encoding="utf-8")
    cfg = load_config(cfg_path)
    assert cfg.risk.force_close_timeouts["tennis_first_set_winner"] == 60
    assert cfg.risk.force_close_timeouts["default"] == 300


def test_force_close_timeouts_defaults_to_empty() -> None:
    from src.config.settings import RiskConfig
    rc = RiskConfig(
        max_single_bet_usdc=50, max_bet_pct=0.05,
        confidence_bet_pct={"A": 0.05, "B": 0.035},
    )
    assert rc.force_close_timeouts == {}
