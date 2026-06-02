"""HealthMonitor: scraper down / stale price / consecutive losses / calibration age."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock

from src.orchestration.health_monitor import Alert, HealthMonitor


def _make_monitor(tmp_path: Path, notifier=None, **kwargs) -> HealthMonitor:
    state = tmp_path / "data"
    audit = tmp_path / "logs" / "audit"
    runtime = tmp_path / "logs" / "runtime"
    for d in (state, audit, runtime):
        d.mkdir(parents=True, exist_ok=True)
    fixed_now = kwargs.pop("now", datetime(2026, 6, 2, 18, 0, 0, tzinfo=timezone.utc))
    return HealthMonitor(
        notifier=notifier or Mock(),
        state_dir=state,
        audit_dir=audit,
        runtime_dir=runtime,
        now_fn=lambda: fixed_now,
        **kwargs,
    )


def test_scraper_broken_state_triggers_critical(tmp_path: Path) -> None:
    monitor = _make_monitor(tmp_path)
    health_dir = monitor.state_dir / "basketball_cache" / "_health"
    health_dir.mkdir(parents=True)
    (health_dir / "sources_status.json").write_text(
        '{"acb": {"state": "broken", "last_fail": "2026-06-02T17:00", "error": "HTTP 403"}}'
    )
    alerts = monitor.check_all()
    assert any(a.severity == "critical" and "SCRAPER_DOWN_acb" in a.category for a in alerts)


def test_scraper_stale_state_triggers_warning(tmp_path: Path) -> None:
    monitor = _make_monitor(tmp_path)
    health_dir = monitor.state_dir / "basketball_cache" / "_health"
    health_dir.mkdir(parents=True)
    (health_dir / "sources_status.json").write_text(
        '{"bsl": {"state": "stale", "last_success": "2026-06-01T10:00"}}'
    )
    alerts = monitor.check_all()
    assert any(a.severity == "warning" and "SCRAPER_STALE_bsl" in a.category for a in alerts)


def test_scraper_healthy_state_no_alert(tmp_path: Path) -> None:
    monitor = _make_monitor(tmp_path)
    health_dir = monitor.state_dir / "basketball_cache" / "_health"
    health_dir.mkdir(parents=True)
    (health_dir / "sources_status.json").write_text(
        '{"acb": {"state": "healthy", "rating_count": 18}}'
    )
    alerts = monitor.check_all()
    scraper_alerts = [a for a in alerts if "SCRAPER" in a.category]
    assert not scraper_alerts


def test_consecutive_losses_triggers_warning(tmp_path: Path) -> None:
    monitor = _make_monitor(tmp_path, consecutive_losses=3)
    history = monitor.audit_dir / "trade_history.jsonl"
    lines = [
        '{"slug":"a","exit_pnl_usdc":-5.0,"exit_timestamp":"2026-06-02T17:00"}',
        '{"slug":"b","exit_pnl_usdc":-3.0,"exit_timestamp":"2026-06-02T17:10"}',
        '{"slug":"c","exit_pnl_usdc":-2.0,"exit_timestamp":"2026-06-02T17:20"}',
    ]
    history.write_text("\n".join(lines))
    alerts = monitor.check_all()
    assert any(a.category == "CONSECUTIVE_LOSSES" for a in alerts)


def test_consecutive_with_win_no_alert(tmp_path: Path) -> None:
    """Son N exit'in BİRİ kâr ise alert YOK."""
    monitor = _make_monitor(tmp_path, consecutive_losses=3)
    history = monitor.audit_dir / "trade_history.jsonl"
    lines = [
        '{"slug":"a","exit_pnl_usdc":-5.0}',
        '{"slug":"b","exit_pnl_usdc":3.0}',   # kâr
        '{"slug":"c","exit_pnl_usdc":-2.0}',
    ]
    history.write_text("\n".join(lines))
    alerts = monitor.check_all()
    assert not any(a.category == "CONSECUTIVE_LOSSES" for a in alerts)


def test_dedupe_prevents_repeated_alert(tmp_path: Path) -> None:
    """Aynı alert dedupe_window içinde tekrar gönderilmez."""
    notifier = Mock()
    fixed_now = datetime(2026, 6, 2, 18, 0, 0, tzinfo=timezone.utc)
    monitor = _make_monitor(tmp_path, notifier=notifier, dedupe_window_minutes=30, now=fixed_now)
    health_dir = monitor.state_dir / "basketball_cache" / "_health"
    health_dir.mkdir(parents=True)
    (health_dir / "sources_status.json").write_text(
        '{"acb": {"state": "broken"}}'
    )
    alerts = monitor.check_all()
    monitor.send_alerts(alerts)
    assert notifier.send.call_count == 1
    # 2. çağrı: aynı window içinde → dedupe
    monitor.send_alerts(alerts)
    assert notifier.send.call_count == 1


def test_dedupe_window_expires_resends(tmp_path: Path) -> None:
    """Dedupe window aştıktan sonra alert tekrar gönderilir."""
    notifier = Mock()
    times = [
        datetime(2026, 6, 2, 18, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 6, 2, 19, 0, 0, tzinfo=timezone.utc),  # +60dk
    ]
    idx = [0]
    def now_fn():
        return times[idx[0]]
    monitor = HealthMonitor(
        notifier=notifier,
        state_dir=tmp_path / "data",
        audit_dir=tmp_path / "logs" / "audit",
        runtime_dir=tmp_path / "logs" / "runtime",
        dedupe_window_minutes=30,
        now_fn=now_fn,
    )
    (monitor.state_dir / "basketball_cache" / "_health").mkdir(parents=True)
    (monitor.state_dir / "basketball_cache" / "_health" / "sources_status.json").write_text(
        '{"acb": {"state": "broken"}}'
    )
    alerts = monitor.check_all()
    monitor.send_alerts(alerts)
    assert notifier.send.call_count == 1
    idx[0] = 1
    monitor.send_alerts(alerts)
    assert notifier.send.call_count == 2


def test_calibration_age_old_triggers_info(tmp_path: Path) -> None:
    monitor = _make_monitor(tmp_path)
    calib = monitor.state_dir / "tennis_calibration.json"
    calib.write_text("{}")
    # 10 gün önce mtime
    old = (datetime.now() - timedelta(days=10)).timestamp()
    import os
    os.utime(calib, (old, old))
    alerts = monitor.check_all()
    assert any(a.severity == "info" and a.category == "CALIBRATION_AGE" for a in alerts)


def test_disabled_notifier_no_send(tmp_path: Path) -> None:
    """notifier=None → send_alerts no-op (crash yok)."""
    monitor = _make_monitor(tmp_path, notifier=None)
    monitor.notifier = None
    alerts = [Alert(severity="critical", category="TEST", message="x")]
    monitor.send_alerts(alerts)  # no crash beklenir
