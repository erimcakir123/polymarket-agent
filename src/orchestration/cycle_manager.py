"""Cycle manager — heavy/light interleave + exit-triggered heavy (DECISIONS §4).

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
        # SPEC-M: Adaptive cycle — en yakin macin saatleri (None=bilinmiyor, default davranis)
        self._nearest_match_hours: float | None = None

    # ── Public API ──

    def signal_exit_happened(self) -> None:
        """Light cycle'da bir exit işlendi — sonraki tick heavy tetikle."""
        self._exit_triggered_pending = True

    def update_nearest_match_hours(self, hours: float | None) -> None:
        """SPEC-M: Agent.py heavy cycle sonrası en yakın maç saatini günceller.
        None = bilgi yok (cold start, scan boş) → default heavy/night davranışı.
        Geçmiş (negatif) saatler caller tarafından filtrelenip None geçilmeli.
        """
        self._nearest_match_hours = hours

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
        """Aktif heavy cycle interval'i saniye olarak (SPEC-M adaptive).

        Sıralı kontrol:
        1. Imminent: nearest_match < imminent_threshold (1h) → imminent_interval (10dk)
        2. Near: nearest_match < near_threshold (3h) → near_interval (15dk)
        3. Maç bilgisi yok ya da uzak:
           - Gece (UTC 08-13) ise night_interval (60dk)
           - Aksi heavy_interval (30dk)

        Adaptive maç varken gece kuralını override eder (maç önemli).
        """
        nearest = self._nearest_match_hours
        if nearest is not None and nearest > 0:
            if nearest < self.config.imminent_threshold_hours:
                return self.config.imminent_interval_min * 60
            if nearest < self.config.near_threshold_hours:
                return self.config.near_interval_min * 60
        # Fallback: gece / gündüz
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
