"""Refresh interval kararı — maç-pencere farkındalıklı.

Saf domain mantığı (I/O yok). Çağıran orchestration bot uptime sırasında
bunu çağırır ve dönen aralığı uyku süresi olarak kullanır.

Sıklık katmanları:
  - LIVE: bir lig maçı şu anda oynanıyor → 5 dk
  - POST_GAME: son maç bittikten sonraki 60 dk → 5 dk
  - PRE_GAME: ilk maç başlamasına 2 saatten az kaldı → 5 dk
  - IDLE: yukarıdakilerin hiçbiri → 6 saat
"""
from __future__ import annotations

from datetime import datetime, timedelta
from enum import IntEnum
from typing import Iterable


class RefreshIntervalSec(IntEnum):
    LIVE = 300       # 5 dakika
    POST_GAME = 300  # 5 dakika
    PRE_GAME = 300   # 5 dakika
    IDLE = 21600     # 6 saat


_POST_GAME_WINDOW = timedelta(minutes=60)
_PRE_GAME_WINDOW = timedelta(hours=2)


def _parse(ts: str | None) -> datetime | None:
    if ts is None:
        return None
    return datetime.fromisoformat(ts.replace("Z", ""))


def decide_refresh_interval(
    now: datetime,
    games_today: Iterable[dict],
) -> RefreshIntervalSec:
    """Bugünün maç takvimine bakıp şu anki uygun refresh aralığını seç.

    `games_today`: her öğe en az `{"start_utc": str, "end_utc": str | None}`.
    end_utc None ise maç hâlâ devam ediyor varsayılır.
    """
    games = list(games_today)
    if not games:
        return RefreshIntervalSec.IDLE
    for g in games:
        start = _parse(g.get("start_utc"))
        end = _parse(g.get("end_utc"))
        if start is None:
            continue
        # Live: başladı ve bitmedi
        if start <= now and end is None:
            return RefreshIntervalSec.LIVE
        # Live: başladı ve süresi devam ediyor
        if start <= now and end is not None and end > now:
            return RefreshIntervalSec.LIVE
        # Post-game window
        if end is not None and end <= now <= end + _POST_GAME_WINDOW:
            return RefreshIntervalSec.POST_GAME
        # Pre-game window
        if start > now and (start - now) <= _PRE_GAME_WINDOW:
            return RefreshIntervalSec.PRE_GAME
    return RefreshIntervalSec.IDLE
