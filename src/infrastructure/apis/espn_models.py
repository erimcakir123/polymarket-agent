"""ESPN client domain modelleri ve parse helper'ları.

Bölünme nedeni: ARCH_GUARD §3 (espn_client.py 400 satır limitini aştı).
Saf dataclass + parse helper'lar — I/O yok, sadece veri şekli ve dönüşüm.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ESPNMatchScore:
    """ESPN scoreboard API'den gelen tek bir maçın skor bilgisi."""

    event_id: str
    home_name: str
    away_name: str
    home_team_id: str = ""
    away_team_id: str = ""
    home_score: int | None = None
    away_score: int | None = None
    period: str = ""
    is_completed: bool = False
    is_live: bool = False
    last_updated: str = ""
    commence_time: str = ""
    inning: int | None = None
    inning_half: str | None = None
    period_number: int | None = None
    clock_seconds: int | None = None
    raw_status: dict[str, Any] = field(default_factory=dict)


def parse_clock_to_seconds(clock: str) -> int | None:
    if not clock or not isinstance(clock, str):
        return None
    parts = clock.strip().split(":")
    if len(parts) != 2:
        return None
    try:
        minutes = int(parts[0])
        seconds = int(parts[1])
    except (ValueError, TypeError):
        return None
    if minutes < 0 or seconds < 0 or seconds >= 60:
        return None
    return minutes * 60 + seconds


def parse_inning_half(short_detail: str) -> str | None:
    if not short_detail:
        return None
    s = short_detail.strip().lower()
    if s.startswith("top"):
        return "top"
    if s.startswith("bot"):
        return "bottom"
    return None


def parse_score(raw: Any) -> int | None:
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (ValueError, TypeError):
        return None
