"""exit_processor.py — trade_logger öncelik sırası testi.

Trade logger disk yazımı, portfolio mutation'dan ÖNCE gerçekleşmeli.
Aksi halde crash sonrası orphan trade oluşur (pozisyon silindi ama
trade_history güncellenmedi).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.models.enums import ExitReason
from src.models.position import Position
from src.orchestration.exit_processor import ExitProcessor
from src.strategy.exit.monitor import ExitSignal


# ── Helpers ──

def _pos(**over) -> Position:
    base = dict(
        condition_id="cond_1", token_id="tok_1", direction="BUY_YES",
        entry_price=0.50, size_usdc=50, shares=100,
        current_price=0.95, anchor_probability=0.55,
        confidence="A", sport_tag="nba",
        match_start_iso="2026-04-17T10:00:00Z",
    )
    base.update(over)
    return Position(**base)


@dataclass
class _CallRecorder:
    """Operasyonların çağrılma sırasını kaydeder."""
    calls: list[str] = field(default_factory=list)


def _make_deps(recorder: _CallRecorder) -> MagicMock:
    """ExitProcessor.deps mock'u — her operasyon recorder'a yazılır."""
    deps = MagicMock()

    # Portfolio
    def mock_remove(cid, realized_pnl_usdc=0.0):
        recorder.calls.append("remove_position")
        return _pos()
    deps.state.portfolio.remove_position.side_effect = mock_remove

    def mock_apply_partial(cid, basis_returned_usdc=0.0, realized_usdc=0.0):
        recorder.calls.append("apply_partial_exit")
    deps.state.portfolio.apply_partial_exit.side_effect = mock_apply_partial

    # Circuit breaker
    def mock_record_exit(pnl_usd=0.0):
        recorder.calls.append("circuit_breaker")
    deps.state.circuit_breaker.record_exit.side_effect = mock_record_exit

    # Cooldown
    def mock_cooldown(win=True):
        recorder.calls.append("cooldown")
    deps.cooldown.record_outcome.side_effect = mock_cooldown

    # Executor
    deps.executor.exit_position.return_value = {"status": "ok"}

    # Price feed
    deps.price_feed = None

    # Trade logger
    def mock_update_on_exit(cid, data):
        recorder.calls.append("trade_logger_update")
        return True
    deps.trade_logger.update_on_exit.side_effect = mock_update_on_exit

    def mock_log_partial(condition_id, tier, sell_pct, realized_pnl_usdc,
                         timestamp, price):
        recorder.calls.append("trade_logger_partial")
        return True
    deps.trade_logger.log_partial_exit.side_effect = mock_log_partial

    # Config
    deps.config = None

    return deps


# ── Tests ──

def test_full_exit_trade_logger_before_remove_position() -> None:
    """Full exit: trade_logger.update_on_exit, remove_position'dan ÖNCE çağrılmalı."""
    recorder = _CallRecorder()
    deps = _make_deps(recorder)
    proc = ExitProcessor(deps)

    pos = _pos()
    signal = ExitSignal(reason=ExitReason.NEAR_RESOLVE, detail="test")
    proc._execute_exit(pos, signal)

    logger_idx = recorder.calls.index("trade_logger_update")
    remove_idx = recorder.calls.index("remove_position")
    assert logger_idx < remove_idx, (
        f"trade_logger ({logger_idx}) must be called BEFORE remove_position ({remove_idx}). "
        f"Call order: {recorder.calls}"
    )


def test_partial_exit_trade_logger_before_portfolio_mutation() -> None:
    """Partial exit: trade_logger.log_partial_exit, apply_partial_exit'ten ÖNCE çağrılmalı."""
    recorder = _CallRecorder()
    deps = _make_deps(recorder)
    proc = ExitProcessor(deps)

    pos = _pos(unrealized_pnl_usdc=45.0)
    signal = ExitSignal(
        reason=ExitReason.SCALE_OUT, partial=True,
        sell_pct=0.4, tier=1, detail="test",
    )
    proc._execute_exit(pos, signal)

    logger_idx = recorder.calls.index("trade_logger_partial")
    portfolio_idx = recorder.calls.index("apply_partial_exit")
    assert logger_idx < portfolio_idx, (
        f"trade_logger ({logger_idx}) must be called BEFORE apply_partial_exit ({portfolio_idx}). "
        f"Call order: {recorder.calls}"
    )


# ── Archive tests (SPEC-009) ──

def _make_deps_with_archive(recorder: _CallRecorder, tmp_path) -> MagicMock:
    """_make_deps'in archive_logger eklenmiş versiyonu."""
    from src.infrastructure.persistence.archive_logger import ArchiveLogger
    deps = _make_deps(recorder)
    deps.archive_logger = ArchiveLogger(str(tmp_path / "archive"))
    return deps


def test_full_exit_writes_to_archive(tmp_path) -> None:
    """Full exit → exits.jsonl'e yazilir (SPEC-009)."""
    import json
    recorder = _CallRecorder()
    deps = _make_deps_with_archive(recorder, tmp_path)
    proc = ExitProcessor(deps)

    pos = _pos(current_price=0.95, slug="team-a-wins")
    signal = ExitSignal(reason=ExitReason.NEAR_RESOLVE, detail="test")
    proc._execute_exit(pos, signal)

    exits_file = deps.archive_logger.dir / "exits.jsonl"
    assert exits_file.exists(), "exits.jsonl olusturulmadi"
    lines = exits_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1, f"1 satir beklendi, {len(lines)} satir bulundu"
    data = json.loads(lines[0])
    assert data["exit_reason"] == "near_resolve"
    assert data["exit_price"] == pytest.approx(0.95)
    assert data["slug"] == "team-a-wins"


def test_partial_exit_writes_to_archive(tmp_path) -> None:
    """Scale-out partial exit → exits.jsonl'e yazilir (SPEC-009)."""
    import json
    recorder = _CallRecorder()
    deps = _make_deps_with_archive(recorder, tmp_path)
    proc = ExitProcessor(deps)

    pos = _pos(unrealized_pnl_usdc=45.0, current_price=0.80, slug="team-b-wins")
    signal = ExitSignal(
        reason=ExitReason.SCALE_OUT, partial=True,
        sell_pct=0.4, tier=1, detail="test",
    )
    proc._execute_exit(pos, signal)

    exits_file = deps.archive_logger.dir / "exits.jsonl"
    assert exits_file.exists(), "exits.jsonl olusturulmadi"
    lines = exits_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1, f"1 satir beklendi, {len(lines)} satir bulundu"
    data = json.loads(lines[0])
    assert data["exit_reason"] == "scale_out"
    assert data["slug"] == "team-b-wins"
    assert data["exit_price"] == pytest.approx(0.80)


def test_no_archive_logger_does_not_crash() -> None:
    """archive_logger yoksa (None) sessizce atlar — hata vermez (SPEC-009)."""
    recorder = _CallRecorder()
    deps = _make_deps(recorder)
    deps.archive_logger = None
    proc = ExitProcessor(deps)

    pos = _pos(current_price=0.95)
    signal = ExitSignal(reason=ExitReason.NEAR_RESOLVE, detail="test")
    # Hata vermeden tamamlanmali
    proc._execute_exit(pos, signal)
