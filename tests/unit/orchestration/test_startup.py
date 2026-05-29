"""startup.py için birim testler — state restore."""
from __future__ import annotations

import json
from pathlib import Path

from src.config.settings import AppConfig
from src.orchestration.startup import bootstrap, persist


def test_cold_bootstrap_starts_fresh(tmp_path: Path) -> None:
    cfg = AppConfig()
    state = bootstrap(cfg, logs_dir=tmp_path, trade_history_path=tmp_path / "trade_history.jsonl")
    assert state.portfolio.bankroll == cfg.initial_bankroll
    assert state.portfolio.count() == 0
    assert state.circuit_breaker.state.breaker_active_until is None
    assert len(state.blacklist.condition_ids) == 0


def test_persist_then_restore_roundtrip(tmp_path: Path) -> None:
    cfg = AppConfig()
    state1 = bootstrap(cfg, logs_dir=tmp_path, trade_history_path=tmp_path / "trade_history.jsonl")

    # Durumu manuel değiştir
    from src.models.position import Position
    pos = Position(
        condition_id="c1", token_id="t", direction="BUY_YES",
        entry_price=0.40, size_usdc=40, shares=100,
        current_price=0.40, anchor_probability=0.55,
        event_id="e1", slug="some-slug",
    )
    state1.portfolio.add_position(pos)
    state1.circuit_breaker.record_exit(pnl_usd=-10, portfolio_value=1000)
    state1.blacklist.add_condition("bad_cid")

    persist(state1)

    # Yeni bootstrap → restore
    state2 = bootstrap(cfg, logs_dir=tmp_path, trade_history_path=tmp_path / "trade_history.jsonl")
    assert state2.portfolio.count() == 1
    assert "c1" in state2.portfolio.positions
    assert state2.blacklist.is_blacklisted(condition_id="bad_cid") is True
    # Circuit breaker state restored
    assert state2.circuit_breaker.state.daily_realized_pnl_pct < 0


def test_bootstrap_writes_session_start_when_missing(tmp_path: Path) -> None:
    """Reboot sonrasi data/session_start.json yok -> bootstrap olusturur."""
    cfg = AppConfig()
    bootstrap(cfg, logs_dir=tmp_path, trade_history_path=tmp_path / "trade_history.jsonl")
    p = tmp_path / "session_start.json"
    assert p.exists()
    data = json.loads(p.read_text(encoding="utf-8"))
    assert "iso" in data and data["iso"]


def test_bootstrap_preserves_existing_session_start(tmp_path: Path) -> None:
    """Reload sirasinda mevcut session_start.json korunmali (sirf reboot siler)."""
    existing_iso = "2026-05-25T10:00:00+00:00"
    (tmp_path / "session_start.json").write_text(
        json.dumps({"iso": existing_iso}), encoding="utf-8",
    )
    cfg = AppConfig()
    bootstrap(cfg, logs_dir=tmp_path, trade_history_path=tmp_path / "trade_history.jsonl")
    data = json.loads((tmp_path / "session_start.json").read_text(encoding="utf-8"))
    assert data["iso"] == existing_iso


def test_corrupt_positions_file_safe_fallback(tmp_path: Path) -> None:
    (tmp_path / "positions.json").write_text("{not json", encoding="utf-8")
    cfg = AppConfig()
    state = bootstrap(cfg, logs_dir=tmp_path, trade_history_path=tmp_path / "trade_history.jsonl")
    # Bozuk dosya → fresh portfolio
    assert state.portfolio.count() == 0


def test_corrupt_breaker_file_safe_fallback(tmp_path: Path) -> None:
    (tmp_path / "circuit_breaker_state.json").write_text("{broken", encoding="utf-8")
    cfg = AppConfig()
    state = bootstrap(cfg, logs_dir=tmp_path, trade_history_path=tmp_path / "trade_history.jsonl")
    assert state.circuit_breaker.state.breaker_active_until is None


def test_breaker_config_from_appconfig(tmp_path: Path) -> None:
    cfg = AppConfig()
    state = bootstrap(cfg, logs_dir=tmp_path, trade_history_path=tmp_path / "trade_history.jsonl")
    assert state.circuit_breaker.config.daily_max_loss_pct == cfg.circuit_breaker.daily_max_loss_pct
    assert state.circuit_breaker.config.consecutive_loss_limit == cfg.circuit_breaker.consecutive_loss_limit


def test_persist_creates_all_three_files(tmp_path: Path) -> None:
    cfg = AppConfig()
    state = bootstrap(cfg, logs_dir=tmp_path, trade_history_path=tmp_path / "trade_history.jsonl")
    persist(state)
    assert (tmp_path / "positions.json").exists()
    assert (tmp_path / "circuit_breaker_state.json").exists()
    assert (tmp_path / "blacklist.json").exists()
