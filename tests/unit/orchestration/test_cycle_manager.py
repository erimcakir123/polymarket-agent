"""cycle_manager.py için birim testler."""
from __future__ import annotations

from datetime import datetime, timezone

from src.config.settings import CycleConfig
from src.orchestration.cycle_manager import CycleManager


def _make(now_ts: float = 1000.0, utc_hour: int = 15, **over) -> CycleManager:
    cfg = CycleConfig(heavy_interval_min=30, light_interval_sec=5)
    return CycleManager(
        config=cfg,
        now_fn=lambda: now_ts,
        utc_now_fn=lambda: datetime(2026, 4, 13, utc_hour, tzinfo=timezone.utc),
    )


def test_cold_start_triggers_heavy() -> None:
    cm = _make(now_ts=1000.0)
    t = cm.tick(has_positions=False)
    assert t.run_heavy is True
    assert t.run_light is True
    assert t.reason == "cold_start"


def test_second_tick_soon_light_only() -> None:
    cm = _make(now_ts=1000.0)
    cm.tick(has_positions=False)  # cold start heavy
    # 10 saniye sonra → light only
    cm2 = CycleManager(
        config=cm.config,
        now_fn=lambda: 1010.0,
        utc_now_fn=cm._utc_now,
    )
    cm2._last_heavy_ts = 1000.0  # manuel set
    t = cm2.tick(has_positions=True)
    assert t.run_heavy is False
    assert t.run_light is True


def test_heavy_after_interval() -> None:
    cm = _make(now_ts=1000.0 + 30 * 60 + 1)  # 30 dk + 1 sn sonra
    cm._last_heavy_ts = 1000.0
    t = cm.tick(has_positions=True)
    assert t.run_heavy is True
    assert t.reason == "periodic_heavy"


def test_exit_triggered_heavy() -> None:
    cm = _make(now_ts=1500.0)
    cm._last_heavy_ts = 1000.0  # Heavy daha yeni koştu
    cm.signal_exit_happened()
    t = cm.tick(has_positions=True)
    assert t.run_heavy is True
    assert t.prefer_eligible_queue is True
    assert t.reason == "exit_triggered_heavy"


def test_exit_trigger_consumed_once() -> None:
    cm = _make(now_ts=1500.0)
    cm._last_heavy_ts = 1000.0
    cm.signal_exit_happened()
    t1 = cm.tick(has_positions=True)
    assert t1.run_heavy is True
    # İkinci tick — queue flag temizlendi
    t2 = cm.tick(has_positions=True)
    assert t2.run_heavy is False


def test_sleep_seconds_matches_light_interval() -> None:
    cm = _make()
    assert cm.sleep_seconds() == 5
