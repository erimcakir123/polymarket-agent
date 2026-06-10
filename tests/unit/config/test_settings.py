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
    assert cfg.edge.min_edge == 0.05


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
    """Kökdeki config.yaml geçerli Pydantic olarak yüklenmeli.

    2026-05-29 Phase 1 (unified paper lab): portföy SADECE BASKETBOL'a
    indirildi. NHL/NCAAF/CFL/UFL/MMA/UFC/Boxing/PGA*/LIV*/LPGA* çıkarıldı.
    Tennis (atp/wta) Phase 3'te eklenecek.
    """
    cfg = load_config()  # default Path("config.yaml")
    assert cfg.mode is not None
    assert cfg.initial_bankroll > 0
    assert cfg.edge.min_edge == 0.05
    # Phase 1 sonrası whitelist sadece basket
    for must_have in ("nba", "wnba", "ncaab", "wncaab", "cbb", "euroleague", "nbl"):
        assert must_have in cfg.scanner.allowed_sport_tags, f"{must_have} listede olmalı"
    # Phase 1 sonrası çıkarılanlar OLMAMALI
    for banned_phase1 in (
        "nhl",
        "ncaaf", "cfl", "ufl",
        "mma", "ufc", "boxing",
        "lpga*", "liv*", "pga*",
    ):
        assert banned_phase1 not in cfg.scanner.allowed_sport_tags, (
            f"{banned_phase1} Phase 1'de çıkarıldı"
        )
    # Phase 3 sonrası tennis (tennis + atp + wta) listede OLMALI.
    # Polymarket event-level sport_tag "tennis" döner → fix 2026-05-29:
    # whitelist'e "tennis" eklendi (yoksa 949 tennis market reddediliyordu).
    for tennis_tag in ("tennis", "atp", "wta"):
        assert tennis_tag in cfg.scanner.allowed_sport_tags, (
            f"{tennis_tag} Phase 3'te eklendi, listede olmalı"
        )
    # Baseball 2026-05-26 çıkarıldı, hala olmamalı
    for banned_baseball in ("mlb", "milb", "npb", "kbo", "baseball"):
        assert banned_baseball not in cfg.scanner.allowed_sport_tags, (
            f"{banned_baseball} 2026-05-26'da çıkarıldı"
        )
    # Draw-possible sporlar MVP dışı
    for banned in ("soccer_epl", "soccer_laliga"):
        assert banned not in cfg.scanner.allowed_sport_tags, f"{banned} MVP dışı"
    # Hockey alt ligleri (NHL artık tamamen yok)
    for hockey_minor in ("ahl", "liiga", "mestis", "shl", "allsvenskan"):
        assert hockey_minor not in cfg.scanner.allowed_sport_tags, (
            f"{hockey_minor} eklenmez"
        )


def test_force_close_timeouts_default_is_empty_dict() -> None:
    """Boş default → feature devre dışı (yaml override etmedikçe)."""
    cfg = AppConfig()
    assert cfg.risk.force_close_timeouts == {}


def test_force_close_timeouts_yaml_override_parses(tmp_path: Path) -> None:
    p = tmp_path / "cfg.yaml"
    p.write_text(
        "risk:\n"
        "  force_close_timeouts:\n"
        "    nba_match_winner: 180\n"
        "    default: 300\n",
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.risk.force_close_timeouts["nba_match_winner"] == 180
    assert cfg.risk.force_close_timeouts["default"] == 300
