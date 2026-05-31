"""Refresh orchestrator — primary çağır, başarısızsa secondary'ye düş.

ARCH_GUARD §12: try/except sadece infrastructure'da. Hata yakalanır,
loglanır, yedek denenir. İkisi de fail ise degrade — boş liste döner.
Çağıran orchestration "boş" durumunu bookmaker fallback olarak değerlendirir.

Tennis Sackmann pattern paralel: birincil kaynak fail-fast ile yedeğe geçer,
sağlık takibi (HealthTracker) 3-fail eşiğinde kaynağı deaktif eder.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from src.infrastructure.data.basketball.data_source_health import HealthTracker
from src.infrastructure.data.basketball.schemas import GameRecord

logger = logging.getLogger(__name__)


@dataclass
class RefreshOutcome:
    games: list[GameRecord]
    source_used: Optional[str]   # "nba_api" | "espn" | None


class BasketballRefreshRunner:
    """Tek lig için primary → secondary refresh akışını koordine eder."""

    def __init__(
        self,
        league: str,
        health_path: Path,
        primary_fetch: Callable[[], list[GameRecord]],
        secondary_fetch: Callable[[], list[GameRecord]],
        now_utc_str: Callable[[], str],
    ) -> None:
        self._league = league
        self._tracker = HealthTracker(health_path)
        self._primary = primary_fetch
        self._secondary = secondary_fetch
        self._now = now_utc_str

    def run(self) -> RefreshOutcome:
        # 1. Primary
        if self._tracker.is_active("nba_api"):
            try:
                games = self._primary()
                self._tracker.record_success("nba_api", at_utc=self._now())
                logger.info(
                    "basketball refresh: nba_api OK, %d games (%s)",
                    len(games), self._league,
                )
                return RefreshOutcome(games=games, source_used="nba_api")
            except Exception as exc:  # noqa: BLE001 — infra boundary
                logger.warning("basketball refresh: nba_api failed — %s", exc)
                self._tracker.record_failure("nba_api", at_utc=self._now())
        # 2. Secondary
        if self._tracker.is_active("espn"):
            try:
                games = self._secondary()
                self._tracker.record_success("espn", at_utc=self._now())
                logger.info(
                    "basketball refresh: espn OK, %d games (%s)",
                    len(games), self._league,
                )
                return RefreshOutcome(games=games, source_used="espn")
            except Exception as exc:  # noqa: BLE001 — infra boundary
                logger.warning("basketball refresh: espn failed — %s", exc)
                self._tracker.record_failure("espn", at_utc=self._now())
        logger.error(
            "basketball refresh: BOTH sources failed for league=%s — degrade",
            self._league,
        )
        return RefreshOutcome(games=[], source_used=None)
