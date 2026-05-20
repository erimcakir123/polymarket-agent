"""tennis_factory trade + skipped logger path wiring (Stage 9 PLAN-TENNIS-001 fix).

Bug: factory `trade_logger`/`skipped_logger`'ı root `logs/` altına yazıyordu
ama dashboard `read_trades` session/+audit/ + `read_skipped` runtime/ okuyor.
Sonuç: tennis cycle'ı kayıt üretiyor ama Exited/Skipped sekmesi boş.

Bu testler, dashboard'un beklediği path'lere dual-write/runtime wire'ı kanıtlar.
Stage 6 equity_logger için aynı kontratın iki kardeşi.
"""
from __future__ import annotations

from pathlib import Path

from src.orchestration.tennis_factory import build_tennis_deps


def _build(tmp_path: Path):
    config_path = Path(__file__).resolve().parents[3] / "config_tennis.yaml"
    if not config_path.exists():
        import pytest  # noqa: PLC0415
        pytest.skip(f"config_tennis.yaml not at {config_path}")
    logs_dir = tmp_path / "logs"
    data_dir = tmp_path / "data"
    deps = build_tennis_deps(
        config_path=config_path,
        data_dir=data_dir,
        logs_dir=logs_dir,
    )
    return deps, logs_dir


def test_trade_logger_writes_to_session_path(tmp_path: Path) -> None:
    """trade_logger mirror = logs/session/trade_history.jsonl.

    Dashboard `read_trades` session/+audit/ birleşimini okuyor; session/ mirror
    olmazsa Exited tab fresh cycle data'sını göstermez.
    """
    deps, logs_dir = _build(tmp_path)
    # Mirror path test-readable — TradeHistoryLogger primary+mirror dual-writes.
    # entry_processor.deps üzerinden trade_logger'a erişim:
    trade_logger = deps.entry_processor.deps.trade_logger
    session_target = logs_dir / "session" / "trade_history.jsonl"
    assert trade_logger.mirror == session_target, (
        f"trade_logger mirror={trade_logger.mirror}; "
        f"dashboard read_trades expects {session_target}"
    )


def test_trade_logger_mirrors_to_audit_path(tmp_path: Path) -> None:
    """trade_logger primary = logs/audit/trade_history.jsonl (ground truth).

    Audit reboot dokunmaz; crash recovery + read_trades fallback.
    """
    deps, logs_dir = _build(tmp_path)
    trade_logger = deps.entry_processor.deps.trade_logger
    audit_target = logs_dir / "audit" / "trade_history.jsonl"
    assert Path(trade_logger.path) == audit_target, (
        f"trade_logger primary={trade_logger.path}; "
        f"audit ground truth expects {audit_target}"
    )


def test_skipped_logger_writes_to_dashboard_readable_path(tmp_path: Path) -> None:
    """skipped_logger = logs/runtime/skipped_trades.jsonl.

    Dashboard `read_skipped` ONLY okuyor `runtime/skipped_trades.jsonl`;
    root logs/skipped_trades.jsonl deprecated — Skipped tab boş kalırdı.
    """
    deps, logs_dir = _build(tmp_path)
    skipped_logger = deps.entry_processor.deps.skipped_logger
    runtime_target = logs_dir / "runtime" / "skipped_trades.jsonl"
    assert Path(skipped_logger.path) == runtime_target, (
        f"skipped_logger path={skipped_logger.path}; "
        f"dashboard read_skipped expects {runtime_target}"
    )
