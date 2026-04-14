"""Cycle manager — heavy/light interleave + exit-triggered heavy (TDD §4).

Davranış:
  - Heavy cycle: varsayılan 30 dk, gece (UTC 08-13) 60 dk.
  - Light cycle: 5 sn (exit check + position mark-to-market + save).
  - Exit-triggered heavy: light cycle'da exit olduğunda cycle_manager'a bildirilir;
    sonraki tick'te heavy cycle zorla tetiklenir (sıradaki 30dk beklemek yerine).

Pure timing — iş mantığı yok. agent.py bu sınıfı çağırır, "şimdi heavy mi light mi
tetiklensin?" sorusunun cevabını alır.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from src.config.settings import CycleConfig

logger = logging.getLogger(__name__)


@dataclass
class CycleTick:
    """Bir tick sonrası hangi cycle çalıştırılmalı."""
    run_heavy: bool
    run_light: bool
    prefer_eligible_queue: bool = False  # Exit-triggered heavy ise True
    reason: str = ""


class CycleManager:
    """Heavy/light scheduling + exit-triggered heavy."""

    def __init__(
        self,
        config: CycleConfig,
        now_fn=time.time,
        utc_now_fn=lambda: datetime.now(timezone.utc),
    ) -> None:
        self.config = config
        self._now = now_fn
        self._utc_now = utc_now_fn
        self._last_heavy_ts: float = 0.0
        self._exit_triggered_pending: bool = False

    # ── Public API ──

    def signal_exit_happened(self) -> None:
        """Light cycle'da bir exit işlendi — sonraki tick heavy tetikle."""
        self._exit_triggered_pending = True

    def tick(self, has_positions: bool) -> CycleTick:
        """Her ana döngü yinelemesinde çağrılır. Ne yapılması gerektiğini döndürür."""
        now = self._now()

        # Exit-triggered heavy: queue'daki pazarları değerlendir
        if self._exit_triggered_pending:
            self._exit_triggered_pending = False
            self._last_heavy_ts = now
            return CycleTick(
                run_heavy=True, run_light=True,
                prefer_eligible_queue=True,
                reason="exit_triggered_heavy",
            )

        # Pozisyon yoksa ilk heavy'yi hemen çalıştır (cold start)
        if not has_positions and self._last_heavy_ts == 0:
            self._last_heavy_ts = now
            return CycleTick(run_heavy=True, run_light=True, reason="cold_start")

        # Periyodik heavy
        interval_sec = self._current_heavy_interval_sec()
        time_since_heavy = now - self._last_heavy_ts
        if time_since_heavy >= interval_sec:
            self._last_heavy_ts = now
            return CycleTick(run_heavy=True, run_light=True, reason="periodic_heavy")

        # Light
        return CycleTick(run_heavy=False, run_light=True, reason="light")

    # ── Timing helpers ──

    def _current_heavy_interval_sec(self) -> int:
        """Gece (UTC 08-13) mı? 60 dk; gündüz 30 dk."""
        hour = self._utc_now().hour
        if hour in self.config.night_hours:
            return self.config.night_interval_min * 60
        return self.config.heavy_interval_min * 60

    def sleep_seconds(self) -> int:
        """Tick'ten sonra bir sonraki tick'e kadar uyku süresi (light interval)."""
        return max(1, self.config.light_interval_sec)

    def next_heavy_at_iso(self) -> str:
        """Bir sonraki heavy cycle'ın ISO timestamp'i (UTC).

        Cold start (_last_heavy_ts=0) ise = şimdi. Aksi halde = last_heavy + current interval.
        Dashboard idle countdown için kullanılır.
        """
        if self._last_heavy_ts == 0.0:
            return self._utc_now().isoformat()
        next_ts = self._last_heavy_ts + self._current_heavy_interval_sec()
        return datetime.fromtimestamp(next_ts, tz=timezone.utc).isoformat()
