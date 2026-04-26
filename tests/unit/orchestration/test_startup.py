"""startup.py için birim testler — state restore."""
from __future__ import annotations

import json
from pathlib import Path

from src.config.settings import AppConfig
from src.orchestration.startup import bootstrap, persist


def _logs(tmp_path: Path) -> Path:
    """Standart logs_dir; data/ otomatik tmp_path/data/ olur."""
    return tmp_path / "logs"


def test_cold_bootstrap_starts_fresh(tmp_path: Path) -> None:
    cfg = AppConfig()
    state = bootstrap(cfg, logs_dir=_logs(tmp_path))
    assert state.portfolio.bankroll == cfg.initial_bankroll
    assert state.portfolio.count() == 0
    assert state.circuit_breaker.state.breaker_active_until is None
    assert len(state.blacklist.condition_ids) == 0


def test_persist_then_restore_roundtrip(tmp_path: Path) -> None:
    cfg = AppConfig()
    state1 = bootstrap(cfg, logs_dir=_logs(tmp_path))

    # Durumu manuel değiştir
    from src.models.position import Position
    pos = Position(
        condition_id="c1", token_id="t", direction="BUY_YES",
        entry_price=0.40, size_usdc=40, shares=100,
        current_price=0.40, anchor_probability=0.55,
        event_id="e1", slug="some-slug",
    )
    state1.portfolio.add_position(pos)
    state1.circuit_breaker.record_exit(pnl_usd=-10)
    state1.blacklist.add_condition("bad_cid")

    persist(state1)

    # Yeni bootstrap → restore
    state2 = bootstrap(cfg, logs_dir=_logs(tmp_path))
    assert state2.portfolio.count() == 1
    assert "c1" in state2.portfolio.positions
    assert state2.blacklist.is_blacklisted(condition_id="bad_cid") is True
    # Circuit breaker state restored
    assert state2.circuit_breaker.state.daily_realized_pnl_usd < 0


def test_corrupt_positions_file_safe_fallback(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "positions.json").write_text("{not json", encoding="utf-8")
    cfg = AppConfig()
    state = bootstrap(cfg, logs_dir=_logs(tmp_path))
    # Bozuk dosya → fresh portfolio
    assert state.portfolio.count() == 0


def test_corrupt_breaker_file_safe_fallback(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "circuit_breaker_state.json").write_text("{broken", encoding="utf-8")
    cfg = AppConfig()
    state = bootstrap(cfg, logs_dir=_logs(tmp_path))
    assert state.circuit_breaker.state.breaker_active_until is None


def test_breaker_config_from_appconfig(tmp_path: Path) -> None:
    cfg = AppConfig()
    state = bootstrap(cfg, logs_dir=_logs(tmp_path))
    assert state.circuit_breaker.config.daily_max_loss_pct == cfg.circuit_breaker.daily_max_loss_pct
    assert state.circuit_breaker.config.consecutive_loss_limit == cfg.circuit_breaker.consecutive_loss_limit


def test_persist_creates_all_three_files(tmp_path: Path) -> None:
    cfg = AppConfig()
    state = bootstrap(cfg, logs_dir=_logs(tmp_path))
    persist(state)
    data_dir = tmp_path / "data"
    assert (data_dir / "positions.json").exists()
    assert (data_dir / "circuit_breaker_state.json").exists()
    assert (data_dir / "blacklist.json").exists()
