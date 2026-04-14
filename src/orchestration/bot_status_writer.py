"""Bot status snapshot yazıcı — dashboard için bot_status.json güncellemesi.

Agent'tan ayrıştırıldı (ARCH_GUARD Kural 3: max 400 satır). Tek sorumluluk:
cycle aşama bilgilerini (scanning/analyzing/executing/idle/light) diske yaz.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.infrastructure.persistence.json_store import JsonStore
from src.orchestration.cycle_manager import CycleManager, CycleTick

logger = logging.getLogger(__name__)


class BotStatusWriter:
    """bot_status.json'ı yazan thin wrapper.

    Agent'tan ayrıldı — dashboard'un okuduğu tek JSON. Schema:
    {mode, cycle, stage, stage_at, next_heavy_at, light_alive}.
    """

    def __init__(self, store: JsonStore, cycle_manager: CycleManager) -> None:
        self._store = store
        self._cycle_manager = cycle_manager

    def write_stage(self, mode: str, cycle: str, stage: str) -> None:
        """Aşama snapshot'ı yaz.

        cycle: 'heavy' | 'light'
        stage: 'scanning' | 'analyzing' | 'executing' | 'idle' | 'light'
        """
        try:
            self._store.save({
                "mode": mode,
                "cycle": cycle,
                "stage": stage,
                "stage_at": datetime.now(timezone.utc).isoformat(),
                "next_heavy_at": self._cycle_manager.next_heavy_at_iso(),
                "light_alive": True,
            })
        except OSError as e:
            logger.warning("Bot status stage write failed: %s", e)

    def write_from_tick(self, mode: str, tick: CycleTick) -> None:
        """Cycle sonu snapshot — heavy ise stage='idle', light ise stage='light'."""
        cycle = "heavy" if tick.run_heavy else "light"
        stage = "idle" if tick.run_heavy else "light"
        self.write_stage(mode=mode, cycle=cycle, stage=stage)
