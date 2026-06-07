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
    """HealthTracker array — active=False (3+ ardisik fail) → critical."""
    monitor = _make_monitor(tmp_path)
    health_dir = monitor.state_dir / "basketball_cache" / "_health"
    health_dir.mkdir(parents=True)
    (health_dir / "sources_status.json").write_text(
        '[{"source":"acb","last_success_utc":"2026-06-01T10:00:00+00:00",'
        '"last_fail_utc":"2026-06-02T17:00:00+00:00",'
        '"consecutive_fails":3,"active":false}]'
    )
    alerts = monitor.check_all()
    assert any(a.severity == "critical" and "SCRAPER_DOWN_acb" in a.category for a in alerts)


def test_scraper_stale_state_triggers_warning(tmp_path: Path) -> None:
    """active=True ama last_success_utc > stale_hours → warning."""
    monitor = _make_monitor(tmp_path)
    health_dir = monitor.state_dir / "basketball_cache" / "_health"
    health_dir.mkdir(parents=True)
    # fixed_now 2026-06-02 18:00; last_success 2026-06-01 10:00 = 32h once (> 24h)
    (health_dir / "sources_status.json").write_text(
        '[{"source":"bsl","last_success_utc":"2026-06-01T10:00:00+00:00",'
        '"last_fail_utc":null,"consecutive_fails":0,"active":true}]'
    )
    alerts = monitor.check_all()
    assert any(a.severity == "warning" and "SCRAPER_STALE_bsl" in a.category for a in alerts)


def test_scraper_healthy_state_no_alert(tmp_path: Path) -> None:
    """active=True + last_success_utc taze → alert YOK."""
    monitor = _make_monitor(tmp_path)
    health_dir = monitor.state_dir / "basketball_cache" / "_health"
    health_dir.mkdir(parents=True)
    # fixed_now 2026-06-02 18:00; last_success 2026-06-02 17:30 = 30dk once (< 24h)
    (health_dir / "sources_status.json").write_text(
        '[{"source":"acb","last_success_utc":"2026-06-02T17:30:00+00:00",'
        '"last_fail_utc":null,"consecutive_fails":0,"active":true}]'
    )
    alerts = monitor.check_all()
    scraper_alerts = [a for a in alerts if "SCRAPER" in a.category]
    assert not scraper_alerts


def test_consecutive_losses_triggers_warning(tmp_path: Path) -> None:
    """SPEC-Z17: kaynak trade_events.jsonl; kind='final' event'ler okunur."""
    monitor = _make_monitor(tmp_path, consecutive_losses=3)
    history = monitor.audit_dir / "trade_events.jsonl"
    lines = [
        '{"kind":"final","slug":"a","exit_pnl_usdc":-5.0,"exit_timestamp":"2026-06-02T17:00"}',
        '{"kind":"final","slug":"b","exit_pnl_usdc":-3.0,"exit_timestamp":"2026-06-02T17:10"}',
        '{"kind":"final","slug":"c","exit_pnl_usdc":-2.0,"exit_timestamp":"2026-06-02T17:20"}',
    ]
    history.write_text("\n".join(lines))
    alerts = monitor.check_all()
    assert any(a.category == "CONSECUTIVE_LOSSES" for a in alerts)


def test_consecutive_with_win_no_alert(tmp_path: Path) -> None:
    """Son N exit'in BİRİ kâr ise alert YOK."""
    monitor = _make_monitor(tmp_path, consecutive_losses=3)
    history = monitor.audit_dir / "trade_events.jsonl"
    lines = [
        '{"kind":"final","slug":"a","exit_pnl_usdc":-5.0}',
        '{"kind":"final","slug":"b","exit_pnl_usdc":3.0}',   # kâr
        '{"kind":"final","slug":"c","exit_pnl_usdc":-2.0}',
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
        '[{"source":"acb","last_success_utc":null,"last_fail_utc":"2026-06-02T17:00:00+00:00",'
        '"consecutive_fails":5,"active":false}]'
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
        '[{"source":"acb","last_success_utc":null,"last_fail_utc":"2026-06-02T17:00:00+00:00",'
        '"consecutive_fails":5,"active":false}]'
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
    # mtime: monitörün KENDI saatine göre 10 gün önce (gerçek now ile karışmasın —
    # _now sabit olduğu için datetime.now() kullanmak testi zamana bağımlı kılar).
    old = (monitor._now() - timedelta(days=10)).timestamp()
    import os
    os.utime(calib, (old, old))
    alerts = monitor.check_all()
    assert any(a.severity == "info" and a.category == "CALIBRATION_AGE" for a in alerts)


def test_muted_alert_categories_suppress_send(tmp_path: Path) -> None:
    """SPEC-Z10 (2026-06-03): muted_alert_categories listesindeki kategori
    send_alerts'te sessizce skip edilir, telegram'a düşmez."""
    notifier = Mock()
    monitor = _make_monitor(
        tmp_path, notifier=notifier,
        muted_alert_categories=["SCRAPER_DOWN_acb_scraper", "SCRAPER_STALE_lega_scraper"],
    )
    alerts = [
        Alert(severity="critical", category="SCRAPER_DOWN_acb_scraper", message="x"),
        Alert(severity="warning", category="SCRAPER_STALE_lega_scraper", message="y"),
        Alert(severity="critical", category="SCRAPER_DOWN_vtb_scraper", message="z"),  # MUTED DEĞİL
        Alert(severity="warning", category="CONSECUTIVE_LOSSES", message="w"),  # MUTED DEĞİL
    ]
    monitor.send_alerts(alerts)
    # Sadece muted DEĞİL olanlar gönderildi
    assert notifier.send.call_count == 2
    sent_msgs = [call.args[0] for call in notifier.send.call_args_list]
    assert any("SCRAPER_DOWN_vtb_scraper" in m for m in sent_msgs)
    assert any("CONSECUTIVE_LOSSES" in m for m in sent_msgs)
    # ACB ve Lega muted → notifier'a hiç gitmedi
    assert not any("SCRAPER_DOWN_acb_scraper" in m for m in sent_msgs)
    assert not any("SCRAPER_STALE_lega_scraper" in m for m in sent_msgs)


def test_disabled_notifier_no_send(tmp_path: Path) -> None:
    """notifier=None → send_alerts no-op (crash yok)."""
    monitor = _make_monitor(tmp_path, notifier=None)
    monitor.notifier = None
    alerts = [Alert(severity="critical", category="TEST", message="x")]
    monitor.send_alerts(alerts)  # no crash beklenir
