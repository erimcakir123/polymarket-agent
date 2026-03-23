"""Dynamic cycle interval based on market conditions."""
from __future__ import annotations
import logging

from src.config import CycleConfig

logger = logging.getLogger(__name__)


class CycleTimer:
    def __init__(self, config: CycleConfig) -> None:
        self.config = config
        self._override: int | None = None
        self._override_cycles: int = 0

    def get_interval(self) -> int:
        if self._override and self._override_cycles > 0:
            return self._override
        return self.config.default_interval_min

    def signal_breaking_news(self, duration_cycles: int = 3) -> None:
        self._override = self.config.breaking_news_interval_min
        self._override_cycles = duration_cycles
        logger.info("Cycle shortened to %d min (breaking news)", self._override)

    def signal_near_stop_loss(self, duration_cycles: int = 2) -> None:
        current = self.get_interval()
        target = self.config.near_stop_loss_interval_min
        if target < current:
            self._override = target
            self._override_cycles = duration_cycles
            logger.info("Cycle shortened to %d min (near stop-loss)", target)

    def signal_scout_approaching(self, duration_cycles: int = 6) -> None:
        """Speed up polling when a scouted match is approaching (within 3 hours)."""
        current = self.get_interval()
        target = 5  # 5 min polling near match time
        if target < current:
            self._override = target
            self._override_cycles = duration_cycles
            logger.info("Cycle shortened to %d min (scouted match approaching)", target)

    def signal_night_mode(self, current_hour: int) -> None:
        if current_hour in self.config.night_hours:
            self._override = self.config.night_interval_min
            self._override_cycles = 1
            logger.info("Cycle extended to %d min (night mode)", self._override)

    def signal_market_aware(self, candidate_count: int, position_count: int) -> None:
        """Adjust cycle interval based on market activity."""
        if candidate_count > 5 or position_count > 3:
            target = max(5, self.config.default_interval_min // 2)
            if target < self.get_interval():
                self._override = target
                self._override_cycles = 1
                logger.info("Cycle shortened to %d min (active markets)", target)

    def signal_live_positions(self, duration_cycles: int = 1) -> None:
        """Speed up polling when positions are live on CLOB."""
        current = self.get_interval()
        target = 5
        if target < current:
            self._override = target
            self._override_cycles = duration_cycles
            logger.info("Cycle shortened to %d min (live CLOB positions)", target)

    def tick(self) -> None:
        if self._override_cycles > 0:
            self._override_cycles -= 1
            if self._override_cycles == 0:
                self._override = None
                logger.info("Cycle interval returned to default %d min", self.config.default_interval_min)
