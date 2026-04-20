"""CycleManager.next_heavy_at_iso — bir sonraki heavy cycle'ın ISO timestamp'i."""
from __future__ import annotations

from datetime import datetime, timezone

from src.config.settings import CycleConfig
from src.orchestration.cycle_manager import CycleManager


def test_next_heavy_at_iso_cold_start_returns_now():
    """İlk heavy hiç çalışmamışsa bir sonraki heavy = şimdi (cold start bekliyor)."""
    fixed_now_ts = 1000.0
    fixed_utc = datetime(2026, 4, 15, 15, 0, 0, tzinfo=timezone.utc)
    mgr = CycleManager(
        CycleConfig(),
        now_fn=lambda: fixed_now_ts,
        utc_now_fn=lambda: fixed_utc,
    )
    # _last_heavy_ts = 0 → cold start
    result = mgr.next_heavy_at_iso()
    assert result == fixed_utc.isoformat()


def test_next_heavy_at_iso_uses_30min_interval():
    """last_heavy + 30dk (her zaman aynı interval)."""
    fixed_now_ts = 10_000.0
    fixed_utc = datetime(2026, 4, 15, 15, 0, 0, tzinfo=timezone.utc)
    mgr = CycleManager(
        CycleConfig(),
        now_fn=lambda: fixed_now_ts,
        utc_now_fn=lambda: fixed_utc,
    )
    mgr._last_heavy_ts = fixed_now_ts
    result = mgr.next_heavy_at_iso()
    expected = datetime.fromtimestamp(fixed_now_ts + 1800, tz=timezone.utc).isoformat()
    assert result == expected
